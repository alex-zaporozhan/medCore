import { Box, Button, Stack } from "@mantine/core";
import { Link, useParams } from "react-router-dom";
import { TaskDetailsView } from "@/admin/components/TaskDetailsView";
import { ContextBar } from "@/shared/ui/ContextBar";
import { ROUTE_PATHS } from "@/routePaths";

export default function AdminTaskDetailsPage() {
  const { taskId } = useParams<{ taskId: string }>();

  if (!taskId) return null;

  return (
    <Stack>
      <ContextBar
        title="Задача"
        actions={
          <Button component={Link} to={ROUTE_PATHS.admin.tasks} variant="default" size="sm">
            Назад к Kanban
          </Button>
        }
      />
      <Box p="md">
        <TaskDetailsView taskId={taskId} mode="page" />
      </Box>
    </Stack>
  );
}

