package com.bizoptimize.controller;

import com.bizoptimize.dto.SavingsRequest;
import com.bizoptimize.dto.TaskResponse;
import com.bizoptimize.service.TaskService;
import jakarta.validation.Valid;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/tasks")
public class TaskController {

    private final TaskService taskService;

    public TaskController(TaskService taskService) {
        this.taskService = taskService;
    }

    @PutMapping("/{id}/savings")
    public TaskResponse updateSavings(
            @PathVariable Long id,
            @Valid @RequestBody SavingsRequest request,
            Authentication authentication) {
        return taskService.updateSavings(authentication.getName(), id, request);
    }
}
