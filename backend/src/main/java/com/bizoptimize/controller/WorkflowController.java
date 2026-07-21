package com.bizoptimize.controller;

import com.bizoptimize.dto.WorkflowRequest;
import com.bizoptimize.dto.WorkflowResponse;
import com.bizoptimize.service.WorkflowService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/workflows")
public class WorkflowController {

    private final WorkflowService workflowService;

    public WorkflowController(WorkflowService workflowService) {
        this.workflowService = workflowService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public WorkflowResponse save(
            @Valid @RequestBody WorkflowRequest request, Authentication authentication) {
        return workflowService.save(authentication.getName(), request);
    }

    @GetMapping
    public List<WorkflowResponse> list(Authentication authentication) {
        return workflowService.listForUser(authentication.getName());
    }

    @GetMapping("/{id}")
    public WorkflowResponse get(@PathVariable Long id, Authentication authentication) {
        return workflowService.getForUser(authentication.getName(), id);
    }
}
