import { Button, Container, Text, Title } from "@mantine/core";
import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <Container size="sm" py="xl">
          <Title order={2} mb="md">
            Что-то пошло не так
          </Title>
          <Text c="dimmed" mb="md">
            Приложение не загрузилось. Если открыли с телефона — убедитесь, что
            вы в той же Wi‑Fi, что и компьютер с запущенным фронтом и бэкендом.
          </Text>
          {this.state.error && (
            <Text size="sm" c="red" mb="md">
              {this.state.error.message}
            </Text>
          )}
          <Button onClick={this.handleRetry}>Попробовать снова</Button>
        </Container>
      );
    }
    return this.props.children;
  }
}
