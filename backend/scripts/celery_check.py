"""Verify Celery + Redis: dispatch a real dataset job to the worker and confirm it
processes end-to-end. Requires the worker to be running:
    .venv\\Scripts\\celery.exe -A app.worker.celery_app worker --loglevel=info --pool=solo
"""
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)

from app.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Dataset, DatasetStatus, User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.worker import process_dataset_task  # noqa: E402

SAMPLE = os.path.join(BACKEND, "sample_data", "sample_sensors.csv")

db = SessionLocal()
user = db.query(User).first()
if user is None:
    user = User(email="celery@demo.io", hashed_password=hash_password("secret123"))
    db.add(user)
    db.commit()
    db.refresh(user)

os.makedirs(settings.upload_dir, exist_ok=True)
stored = os.path.join(settings.upload_dir, "celery_test.csv")
shutil.copy(SAMPLE, stored)

ds = Dataset(user_id=user.id, filename="celery_test.csv", status=DatasetStatus.PENDING)
db.add(ds)
db.commit()
db.refresh(ds)
ds_id = ds.id
print(f"dispatching dataset {ds_id} to Celery broker {settings.celery_broker_url} ...")

async_result = process_dataset_task.delay(ds_id, stored)
print("task id:", async_result.id)
payload = async_result.get(timeout=120)  # waits on the Redis result backend
print("worker returned:", payload)

db.expire_all()
ds = db.get(Dataset, ds_id)
print(f"dataset status={ds.status} rows={ds.row_count}")

# cleanup this throwaway dataset
from app.models import Anomaly, EtlRun, SensorReading  # noqa: E402

db.query(Anomaly).filter(Anomaly.dataset_id == ds_id).delete(synchronize_session=False)
db.query(SensorReading).filter(SensorReading.dataset_id == ds_id).delete(synchronize_session=False)
db.query(EtlRun).filter(EtlRun.dataset_id == ds_id).delete(synchronize_session=False)
db.delete(db.get(Dataset, ds_id))
db.commit()
db.close()
print("RESULT:", "PASS" if ds.status == DatasetStatus.COMPLETED else "FAIL")
