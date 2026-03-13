## Business Description (inferred from code)

This document describes the **business logic and product capabilities** of the `dental-booking` system as inferred **only from code and configuration**, without using any architecture or business documentation. It focuses on what the product does for its users, which problems it solves, and how the flows are structured.

---

### 1. Product Overview

`dental-booking` is a **B2B2C platform for dental clinics** that combines:
- A **patient-facing web application** for online booking, payments, notifications, chat, and marketing content.
- A **rich admin panel** for clinic staff to manage doctors, services, schedule, bookings, recalls, marketing, omnichannel messaging, AI‑assisted workflows, and reporting.

The system targets **multi‑clinic dental practices** that need:
- Centralized online appointment management.
- Automated reminders and recalls to reduce no‑shows.
- Omnichannel communication (messengers, SMS, email, Telegram).
- Modern patient experience: online booking, prepayment, chat, and personalized feed.

---

### 2. Key Personas

From the code, the main personas appear to be:

- **Patient**
  - Wants to find a clinic/service/doctor.
  - Wants to book or reschedule appointments online.
  - Expects reminders and easy communication via chat and messaging apps.
  - Wants to understand promotions, discounts, and clinic content.

- **Clinic Administrator / Receptionist**
  - Manages schedule, doctors, and patient flow.
  - Handles daily bookings: creating, confirming, canceling, rescheduling, marking no‑shows/completed.
  - Communicates with patients across channels (phone, messengers, SMS, email).
  - Uses dashboard and reports to track performance.

- **Clinic Owner / Manager**
  - Configures clinics, services, pricing, discounts, notification policies.
  - Sets up payment gateways, omnichannel integrations, AI behavior, and marketing.
  - Reviews analytics and AI‑driven reports.

---

### 3. Core Patient Flows

#### 3.1 Authentication & Onboarding

- Patients can:
  - Log in or sign up using phone/code flows (auth routers and services).
  - Authenticate via OAuth (VK, Yandex), using dedicated OAuth endpoints and frontend pages (`LoginPage`, `OAuthResultPage`).
- The system issues JWT tokens for authenticated calls to patient APIs.

#### 3.2 Discover Clinics, Services, and Doctors

- Public APIs expose:
  - **Clinics**: list and details of clinics available.
  - **Services**: per‑clinic list of services with:
    - Names, descriptions, base prices.
    - Active discounts and effective prices.
  - **Doctors**:
    - Doctors working in the clinic.
    - Their specializations and which services they provide.

Patients can see this information in the patient app and use it as input to the booking wizard.

#### 3.3 Online Booking Wizard

The **booking wizard** (`BookingWizardPage`) implements a multi‑step flow:

1. **Select service**
   - Patient chooses a service from the clinic catalog.
   - UI displays prices and flags whether a discount is active.
2. **Select doctor**
   - List of doctors is filtered to those who provide the selected service.
   - Patient may select a specific doctor or possibly “any available”.
3. **Select date and time slot**
   - System queries schedule endpoints (`schedule` / `doctor schedule`) to show free slots for the selected doctor and service.
   - Slots respect:
     - Doctor working hours.
     - Absences / blocked times.
     - Queue policies (how many patients can be booked per slot).
4. **Confirm booking & payment**
   - Patient confirms details (service, doctor, clinic, time, contact information).
   - If the clinic requires **prepayment** for this service or booking:
     - The backend creates a prepayment request.
     - The frontend either:
       - Redirects to payment provider (YooKassa), or
       - Confirms payment instantly if certain conditions are met.
   - Success leads to the **Booking Success** screen.

The booking is stored as a `Booking` entity with a status such as `pending`, `confirmed`, `completed`, `cancelled`, or `no_show`.

#### 3.4 Booking Management for Patients

- Patients can:
  - View their upcoming and past bookings through patient endpoints (`/api/v1/patient/bookings`).
  - Cancel their own bookings (with validation that they own the booking).
  - See booking statuses reflecting the current state.

The system enforces ownership checks and uses domain services to validate allowed transitions.

#### 3.5 Notifications & Reminders

- Upon **booking creation or cancellation**, Celery tasks create and send notifications via:
  - SMS.
  - Email (if configured).
  - Telegram (if configured).
- Automated **reminders**:
  - 24 hours before the appointment.
  - 2 hours before the appointment.
- Background tasks periodically scan the database for bookings that require reminders, then schedule notifications based on policies and communication preferences.

Patients can adjust their **notification settings** (channels and preferences) via dedicated APIs and UI.

#### 3.6 Chat & Omnichannel Communication (Patient Side)

- Patients have access to a **chat interface** in the app:
  - They can send messages to the clinic.
  - Messages are persisted and linked to an omnichannel chat/contact.
  - Admins can respond from their omnichannel interface.
- Channels may include:
  - Web chat.
  - External messengers connected via integrations (e.g., WhatsApp, Telegram).

#### 3.7 Marketing Feed & Content

- Patients can see:
  - **Stories** and promo posts (like a marketing feed).
  - **Client references** (testimonials).
  - **Discounts** and special offers.
- This content is driven by entities such as `Story`, `PromoPost`, `ClientReference`, `Discount` and exposed via public or patient‑facing endpoints, rendered in pages like `FeedPage`.

---

### 4. Core Admin & Clinic Flows

#### 4.1 Admin Authentication & Clinic Context

- Admins log in via admin auth endpoints and admin login page.
- Admin JWT tokens are used for secure access to admin APIs.
- Admin UI operates in the context of a **selected clinic**:
  - `AdminClinicContext` manages current clinic selection.
  - Many admin APIs require clinic ID to scope data and actions.

#### 4.2 Clinic, Doctor, and Service Management

- **Clinics**
  - Create/update basic clinic information.
  - Configure clinic-specific settings (AI, integrations, notification policies, legal agreements, etc.).

- **Doctors**
  - Manage doctor profiles (name, specialization, active status).
  - Attach doctors to clinics and services (`ServiceDoctor` relationships).

- **Services**
  - Create and configure services (name, description, duration, base price).
  - Assign services to doctors.
  - Set up **discounts** and promo pricing per service or per clinic.

#### 4.3 Schedule & Capacity Management

- Admins configure:
  - **Doctor working hours** and regular schedules.
  - **Absences** and time‑off periods.
  - **Queue policies** to define how slots are filled and overbooked.

- The system:
  - Uses this information to generate available slots for the patient booking wizard.
  - Enforces availability when admins or patients create bookings.

#### 4.4 Booking Operations (Admin Side)

Admins use their UI and corresponding API endpoints to:

- Search and filter bookings by:
  - Date.
  - Doctor.
  - Status.
  - Patient phone or name.
- Perform booking actions:
  - Create bookings manually (e.g., from phone calls).
  - Confirm, cancel, reschedule.
  - Mark no‑shows.
  - Mark appointments as completed.

These operations are implemented as explicit admin endpoints with status transitions validated by booking services.

#### 4.5 Payments, Prepayments, and Policies

- Admins control:
  - **Prepayment policies**:
    - Whether prepayment is required for certain services/clinics.
    - Minimum prepayment amounts or conditions.
  - **Payment gateway settings** (YooKassa keys and parameters).
- The system:
  - Creates and tracks **prepayment transactions**.
  - Associates payments with bookings.
  - Reflects payment status in booking state and UI.

#### 4.6 Omnichannel Chat & Messaging (Admin Side)

The omnichannel subsystem provides admins with a **unified communication console**:

- **Chat list & filters**
  - View list of chats with patients across channels.
  - Filter and search by contact, status, channel, etc.

- **Chat view**
  - Load messages in a conversation with pagination.
  - See message metadata (channel, direction, timestamps).
  - See associated clinic, patient/contact, and context.

- **Sending messages**
  - Admins send replies that:
    - Are stored as `OmnichannelMessage`.
    - Are dispatched via `OmnichannelOutboundDispatcher` to the correct channel.

- **Moderation & audit**
  - Admin can hide specific messages (e.g., for inappropriate content) while keeping:
    - An audit log with admin identity, IP, user agent, and reasons.

- **AI modes**
  - Per‑chat AI mode can be switched between:
    - `AUTO_REPLY` (AI responds automatically).
    - `SUGGEST_ONLY` (AI suggests text for human approval).
    - `DISABLED` (no AI intervention).
  - AI orchestrator and analysis services use these settings to drive behavior.

#### 4.7 Marketing, Feed, and Patient Engagement

- Admins manage:
  - **Stories** (short‑lived or feed-like content).
  - **Promo posts** and banners.
  - **Client references** (testimonials).
  - **Stickers** and visual assets.
  - **Discounts** and promotions tied to services or campaigns.

- The system exposes this content via public/patient APIs and surfaces it in:
  - Patient feed (`FeedPage`).
  - Booking flows (highlighting discounts and promotions).

#### 4.8 Recalls, Waitlists, and Automation

- **Waitlist**
  - Patients can be added to a waitlist when no suitable slots are available.
  - System manages `WaitlistEntry` and `WaitlistNotification` entities.
  - Notifications are sent when matching slots become available.

- **Recalls**
  - Recalls are automated campaigns to bring patients back (e.g., for checkups).
  - Domain entities:
    - `RecallAutomation` — defines trigger rules.
    - `RecallSegment` — defines which patients qualify.
    - `RecallTemplate` — defines message content.
    - `RecallLog` — tracks execution.
  - Background services:
    - Periodically evaluate segments, schedule recall notifications, and log outcomes.

These mechanisms help clinics reduce churn and increase repeat visits.

#### 4.9 Reporting and Analytics

- **Admin dashboard**
  - High‑level KPIs:
    - Number of bookings per status for today.
    - Revenue metrics.
    - Number of new patients.

- **Reports**
  - More detailed reports available via reports pages and APIs.
  - Reports may include time ranges, clinic filtering, and breakdowns by doctor/service.

- **AI‑powered analysis**
  - AI is used to:
    - Analyze conversations.
    - Produce AI reports and insights on clinic performance or communication quality.

---

### 5. AI Features and Governance

- **AI usage areas**
  - Omnichannel chat:
    - Automated replies or suggestions to admins.
  - Conversation analysis:
    - Extract structured insights from chat transcripts.
  - Reporting:
    - AI‑enhanced analytics in dedicated AI reports.

- **Configuration**
  - AI provider URL, model name, and timeouts configured per installation.
  - Clinic‑level and chat‑level AI settings control enablement and aggressiveness.

- **Safety and control**
  - AI sanitization utilities are used to:
    - Remove or obfuscate sensitive information.
    - Enforce content safety before sending or storing data.
  - Rate limits for AI requests per clinic prevent abuse and cost overruns.

---

### 6. Value Proposition (inferred)

From these flows, the platform delivers value by:

- **For patients**
  - Frictionless online booking and prepayment for dental appointments.
  - Transparent services, prices, discounts, and promotional content.
  - Reliable reminders and multi-channel communication.
  - A modern chat‑based interaction model with clinics.

- **For clinics**
  - Consolidated management of schedule, doctors, and bookings across clinics.
  - Reduced no‑shows through prepayments, reminders, and recalls.
  - Centralized omnichannel messaging with moderation and auditability.
  - Strong marketing tools (stories, feed, discounts, stickers, testimonials).
  - Actionable operational insights and AI‑powered analysis.

This document should be treated as a **business-level interpretation of the codebase**, constrained strictly by what is implemented in code today.

