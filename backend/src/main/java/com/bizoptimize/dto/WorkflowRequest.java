package com.bizoptimize.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import java.util.List;

public record WorkflowRequest(
        @NotBlank String title,
        @NotBlank String rawText,
        @NotEmpty List<TaskDto> tasks) {}
