package com.bizoptimize.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.bizoptimize.dto.SavingsRequest;
import com.bizoptimize.dto.TaskResponse;
import com.bizoptimize.model.Task;
import com.bizoptimize.model.User;
import com.bizoptimize.model.Workflow;
import com.bizoptimize.repository.TaskRepository;
import com.bizoptimize.repository.UserRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TaskServiceTest {

    @Mock private TaskRepository taskRepository;
    @Mock private UserRepository userRepository;

    private TaskService taskService;
    private User owner;
    private Task task;

    @BeforeEach
    void setUp() {
        taskService = new TaskService(taskRepository, userRepository, new JsonConverter());

        owner = new User();
        owner.setId(1L);
        owner.setEmail("owner@example.com");

        Workflow workflow = new Workflow();
        workflow.setUser(owner);

        task = new Task();
        task.setId(10L);
        task.setWorkflow(workflow);
        task.setScore(80);
        task.setTaskText("Send a reminder email every time an invoice is overdue.");
    }

    @Test
    void computesSavingsScaledByAutomatabilityScore() {
        when(userRepository.findByEmail("owner@example.com")).thenReturn(Optional.of(owner));
        when(taskRepository.findById(10L)).thenReturn(Optional.of(task));
        when(taskRepository.save(task)).thenReturn(task);

        TaskResponse response =
                taskService.updateSavings("owner@example.com", 10L, new SavingsRequest(5.0, 20.0));

        // 5 hrs/week * 52 weeks * $20/hr * 0.80 automatability = $4160
        assertThat(response.estimatedAnnualSavings()).isEqualTo(4160.0);
        assertThat(response.hoursPerWeek()).isEqualTo(5.0);
        assertThat(response.hourlyRate()).isEqualTo(20.0);
    }
}
