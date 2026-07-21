package com.bizoptimize.service;

import com.bizoptimize.dto.TaskDto;
import com.bizoptimize.dto.TaskResponse;
import com.bizoptimize.dto.WorkflowRequest;
import com.bizoptimize.dto.WorkflowResponse;
import com.bizoptimize.model.Task;
import com.bizoptimize.model.User;
import com.bizoptimize.model.Workflow;
import com.bizoptimize.repository.UserRepository;
import com.bizoptimize.repository.WorkflowRepository;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class WorkflowService {

    private final WorkflowRepository workflowRepository;
    private final UserRepository userRepository;
    private final JsonConverter jsonConverter;

    public WorkflowService(
            WorkflowRepository workflowRepository,
            UserRepository userRepository,
            JsonConverter jsonConverter) {
        this.workflowRepository = workflowRepository;
        this.userRepository = userRepository;
        this.jsonConverter = jsonConverter;
    }

    private User requireUser(String email) {
        return userRepository
                .findByEmail(email)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
    }

    @Transactional
    public WorkflowResponse save(String email, WorkflowRequest request) {
        User user = requireUser(email);

        Workflow workflow = new Workflow();
        workflow.setUser(user);
        workflow.setTitle(request.title());
        workflow.setRawText(request.rawText());

        for (TaskDto taskDto : request.tasks()) {
            Task task = new Task();
            task.setWorkflow(workflow);
            task.setTaskText(taskDto.taskText());
            task.setHint(taskDto.hint());
            task.setScore(taskDto.score());
            task.setExplanation(taskDto.explanation());
            task.setFeaturesJson(jsonConverter.writeMap(taskDto.features()));
            task.setAutomationJson(jsonConverter.writeList(taskDto.automation()));
            task.setAutomationDecision(taskDto.automationDecision());
            workflow.getTasks().add(task);
        }

        Workflow saved = workflowRepository.save(workflow);
        return toResponse(saved);
    }

    @Transactional(readOnly = true)
    public List<WorkflowResponse> listForUser(String email) {
        User user = requireUser(email);
        return workflowRepository.findByUserIdOrderByCreatedAtDesc(user.getId()).stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public WorkflowResponse getForUser(String email, Long workflowId) {
        User user = requireUser(email);
        Workflow workflow =
                workflowRepository
                        .findById(workflowId)
                        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));

        if (!workflow.getUser().getId().equals(user.getId())) {
            // 404 instead of 403 so we don't confirm other users' workflow IDs exist.
            throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        }
        return toResponse(workflow);
    }

    private WorkflowResponse toResponse(Workflow workflow) {
        List<TaskResponse> taskResponses =
                workflow.getTasks().stream()
                        .map(
                                t ->
                                        new TaskResponse(
                                                t.getId(),
                                                t.getTaskText(),
                                                t.getHint(),
                                                t.getScore(),
                                                t.getExplanation(),
                                                jsonConverter.readMap(t.getFeaturesJson()),
                                                jsonConverter.readList(t.getAutomationJson()),
                                                t.getHoursPerWeek(),
                                                t.getHourlyRate(),
                                                t.getEstimatedAnnualSavings(),
                                                t.getAutomationDecision()))
                        .toList();

        return new WorkflowResponse(
                workflow.getId(),
                workflow.getTitle(),
                workflow.getRawText(),
                workflow.getCreatedAt(),
                taskResponses);
    }
}
