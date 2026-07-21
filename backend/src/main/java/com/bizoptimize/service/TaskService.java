package com.bizoptimize.service;

import com.bizoptimize.dto.SavingsRequest;
import com.bizoptimize.dto.TaskResponse;
import com.bizoptimize.model.Task;
import com.bizoptimize.model.User;
import com.bizoptimize.repository.TaskRepository;
import com.bizoptimize.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class TaskService {

    private final TaskRepository taskRepository;
    private final UserRepository userRepository;
    private final JsonConverter jsonConverter;

    public TaskService(
            TaskRepository taskRepository, UserRepository userRepository, JsonConverter jsonConverter) {
        this.taskRepository = taskRepository;
        this.userRepository = userRepository;
        this.jsonConverter = jsonConverter;
    }

    /**
     * ROI heuristic: hours spent annually on the task, times the hourly rate, scaled by the
     * automatability score (a task scored 85/100 is assumed to have ~85% of its time reclaimable
     * once automated, not 100% -- some human oversight/exception-handling typically remains).
     * This is intentionally simple and documented as such in the README; it is not a claim of
     * measured real-world savings.
     */
    @Transactional
    public TaskResponse updateSavings(String email, Long taskId, SavingsRequest request) {
        User user =
                userRepository
                        .findByEmail(email)
                        .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));

        Task task =
                taskRepository
                        .findById(taskId)
                        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));

        if (!task.getWorkflow().getUser().getId().equals(user.getId())) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        }

        double annualHours = request.hoursPerWeek() * 52;
        double automationFraction = task.getScore() / 100.0;
        double estimatedSavings = annualHours * request.hourlyRate() * automationFraction;

        task.setHoursPerWeek(request.hoursPerWeek());
        task.setHourlyRate(request.hourlyRate());
        task.setEstimatedAnnualSavings(Math.round(estimatedSavings * 100.0) / 100.0);

        Task saved = taskRepository.save(task);
        return new TaskResponse(
                saved.getId(),
                saved.getTaskText(),
                saved.getHint(),
                saved.getScore(),
                saved.getExplanation(),
                jsonConverter.readMap(saved.getFeaturesJson()),
                jsonConverter.readList(saved.getAutomationJson()),
                saved.getHoursPerWeek(),
                saved.getHourlyRate(),
                saved.getEstimatedAnnualSavings(),
                saved.getAutomationDecision());
    }
}
