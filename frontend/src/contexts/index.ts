/**
 * Глобальные React-контексты: раздельно админка (`AdminClinic*`) и пациент (`PatientAuth*`).
 * Не смешивать сценарии в одном провайдере (раздельные провайдеры для admin / patient).
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
