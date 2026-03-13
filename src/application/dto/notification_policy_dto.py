"""Notification policy and patient notification settings DTOs."""

from pydantic import BaseModel


class ClinicNotificationPolicyRead(BaseModel):
    allow_patient_disable_discount_notifications: bool
    allow_patient_disable_reminders: bool
    allow_patient_disable_all_notifications: bool


class ClinicNotificationPolicyUpdate(BaseModel):
    allow_patient_disable_discount_notifications: bool | None = None
    allow_patient_disable_reminders: bool | None = None
    allow_patient_disable_all_notifications: bool | None = None


class PatientNotificationSettingsRead(BaseModel):
    disable_discount_notifications: bool
    disable_reminders: bool
    disable_all_notifications: bool


class PatientNotificationSettingsUpdate(BaseModel):
    disable_discount_notifications: bool | None = None
    disable_reminders: bool | None = None
    disable_all_notifications: bool | None = None
