import { useMemo } from "react";
import { useDoctor, usePatient } from "@/hooks";
import { usePersonCard } from "./PersonCardContext";
import { DoctorEntityDrawer } from "@/admin/components/entity/DoctorEntityDrawer";
import { PatientEntityDrawer } from "@/admin/components/entity/PatientEntityDrawer";
import { StaffCardModal } from "./StaffCardModal";

export function PersonCardModalHost() {
  const { target, close } = usePersonCard();

  const doctorId = target?.kind === "doctor" ? target.id : null;
  const patientId = target?.kind === "patient" ? target.id : null;
  const staffId = target?.kind === "staff" ? target.id : null;

  const { data: doctor } = useDoctor(doctorId);
  const { data: patient } = usePatient(patientId);

  const opened = Boolean(target);
  const kind = target?.kind ?? null;

  const showDoctor = opened && kind === "doctor";
  const showPatient = opened && kind === "patient";
  const showStaff = opened && kind === "staff";

  // When switching target, keep the host stable; inner components handle their own loading UX.
  const doctorTitle = useMemo(() => doctor?.full_name ?? "", [doctor?.full_name]);
  const patientTitle = useMemo(() => patient?.full_name ?? patient?.phone ?? "", [patient?.full_name, patient?.phone]);
  void doctorTitle;
  void patientTitle;

  return (
    <>
      <DoctorEntityDrawer
        opened={showDoctor}
        onClose={close}
        doctor={doctor ?? null}
        mode="view"
        presentation="modal"
      />
      <PatientEntityDrawer
        opened={showPatient}
        onClose={close}
        patient={patient ?? null}
        mode="view"
        presentation="modal"
      />
      <StaffCardModal opened={showStaff} onClose={close} adminId={staffId} />
    </>
  );
}

