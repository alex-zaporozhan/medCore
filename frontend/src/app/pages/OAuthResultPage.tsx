import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { Center, Loader, Paper, Stack, Text, Title } from "@mantine/core";
import { useEffect, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ROUTE_PATHS, patientPublicLoginSearch } from "@/routePaths";

function useQueryParams() {
  const { search } = useLocation();
  return useMemo(() => new URLSearchParams(search), [search]);
}

export default function OAuthResultPage() {
  const navigate = useNavigate();
  const { login } = usePatientAuth();
  const params = useQueryParams();

  const oauth = params.get("oauth");
  const status = params.get("status");
  const token = params.get("token");
  const patientId = params.get("patient_id");

  const providerName = oauth === "vk" ? "VK" : oauth === "yandex" ? "Яндекс" : "соцсеть";

  useEffect(() => {
    if (status === "ok" && token && patientId) {
      login(token, patientId);
      const redirect = window.location.pathname.startsWith(ROUTE_PATHS.patient.home)
        ? window.location.pathname
        : ROUTE_PATHS.patient.home;
      navigate(redirect, { replace: true });
      return;
    }

    if (status === "cancelled") {
      navigate(`${ROUTE_PATHS.other.login}${patientPublicLoginSearch("oauth-cancelled")}`, {
        replace: true,
      });
      return;
    }

    if (status && ["error", "state_invalid", "provider_error"].includes(status)) {
      // stay on this page to show error, then redirect back to login after short delay
      const timeout = setTimeout(() => {
        navigate(`${ROUTE_PATHS.other.login}${patientPublicLoginSearch("oauth-error")}`, {
          replace: true,
        });
      }, 3000);
      return () => clearTimeout(timeout);
    }

    navigate(`${ROUTE_PATHS.other.login}${patientPublicLoginSearch("need-clinic")}`, {
      replace: true,
    });
  }, [status, token, patientId, login, navigate]);

  let message = "Обрабатываем результат входа...";
  if (status === "ok") {
    message = `Успешный вход через ${providerName}. Перенаправляем в личный кабинет...`;
  } else if (status === "cancelled") {
    message = `Вы отменили вход через ${providerName}. Возвращаем на страницу логина...`;
  } else if (status && ["error", "state_invalid", "provider_error"].includes(status)) {
    message = `Не удалось войти через ${providerName}. Попробуйте ещё раз или используйте вход по SMS.`;
  }

  return (
    <Center h="100%">
      <Paper radius="lg" shadow="md" p="xl" maw={420} w="100%" withBorder>
        <Stack gap="sm" align="center">
          <Title order={3}>Вход через {providerName}</Title>
          <Loader />
          <Text ta="center">{message}</Text>
        </Stack>
      </Paper>
    </Center>
  );
}

