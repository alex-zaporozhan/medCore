/**
 * Глобальные React-контексты: раздельно админка (`AdminClinic*`) и пациент (`PatientAuth*`).
 * Не смешивать сценарии в одном провайдере — см. техпаспорт §4.
 */
export {
  PatientAuthProvider,
  usePatientAuth,
} from "./PatientAuthContext";
export {
  AdminClinicProvider,
  useAdminClinic,
  useBusinessLexicon,
} from "./AdminClinicContext";
