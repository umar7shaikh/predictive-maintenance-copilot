// Lightweight i18n scaffold (Phase 9). No dependency — a dictionary + a t() helper
// reading the chosen language from localStorage. Extend the dictionaries and call
// t("key") in components. Nav + key labels are wired as a demonstration; full
// page-by-page translation is incremental from here.
//
// Target markets: English, Hindi, Bahasa Malaysia, Thai (add more as needed).

const DICT = {
  en: {
    "nav.fleet": "Fleet", "nav.data": "Data", "nav.detection": "Detection",
    "nav.carbon": "Carbon", "nav.reports": "Reports", "nav.copilot": "Copilot",
    "nav.log": "Log", "nav.org": "Org", "app.signout": "Sign out",
  },
  hi: {
    "nav.fleet": "फ़्लीट", "nav.data": "डेटा", "nav.detection": "पहचान",
    "nav.carbon": "कार्बन", "nav.reports": "रिपोर्ट", "nav.copilot": "कोपायलट",
    "nav.log": "लॉग", "nav.org": "संगठन", "app.signout": "साइन आउट",
  },
  ms: {
    "nav.fleet": "Armada", "nav.data": "Data", "nav.detection": "Pengesanan",
    "nav.carbon": "Karbon", "nav.reports": "Laporan", "nav.copilot": "Kopilot",
    "nav.log": "Log", "nav.org": "Organisasi", "app.signout": "Log keluar",
  },
  th: {
    "nav.fleet": "ฟลีต", "nav.data": "ข้อมูล", "nav.detection": "การตรวจจับ",
    "nav.carbon": "คาร์บอน", "nav.reports": "รายงาน", "nav.copilot": "โคไพลอต",
    "nav.log": "บันทึก", "nav.org": "องค์กร", "app.signout": "ออกจากระบบ",
  },
};

export const LANGUAGES = [
  { code: "en", label: "EN" },
  { code: "hi", label: "हि" },
  { code: "ms", label: "MS" },
  { code: "th", label: "ไทย" },
];

export function getLang() {
  return localStorage.getItem("pdm_lang") || "en";
}

export function setLang(code) {
  localStorage.setItem("pdm_lang", code);
  window.location.reload(); // simplest re-render; swap for context later
}

export function t(key) {
  const lang = getLang();
  return (DICT[lang] && DICT[lang][key]) || DICT.en[key] || key;
}
