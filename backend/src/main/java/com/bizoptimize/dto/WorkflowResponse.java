package com.bizoptimize.dto;

import java.time.Instant;
import java.util.List;

public record WorkflowResponse(
        Long id, String title, String rawText, Instant createdAt, List<TaskResponse> tasks) {}
