import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import MachineDetail from "./pages/MachineDetail.jsx";
import Upload from "./pages/Upload.jsx";
import Assistant from "./pages/Assistant.jsx";
import Logs from "./pages/Logs.jsx";
import Tuning from "./pages/Tuning.jsx";

function Protected({ children }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="machines/:id" element={<MachineDetail />} />
        <Route path="upload" element={<Upload />} />
        <Route path="assistant" element={<Assistant />} />
        <Route path="tuning" element={<Tuning />} />
        <Route path="logs" element={<Logs />} />
      </Route>
    </Routes>
  );
}
