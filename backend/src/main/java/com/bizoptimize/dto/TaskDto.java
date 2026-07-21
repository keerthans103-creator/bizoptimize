package com.bizoptimize.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * Shape matches the ML service's /analyze response for one task (snake_case
 * keys, since that's what the Python service emits), plus one field the
 * frontend adds itself: automation_decision, set from the Feed swipe deck
 * ("AUTOMATE"/"SKIP"), null if the user never swiped on this task.
 */
public record TaskDto(
        @JsonProperty("task_text") String taskText,
        String hint,
        Integer score,
        String explanation,
        Map<String, Object> features,
        List<Map<String, Object>> automation,
        @JsonProperty("automation_decision") String automationDecision) {}
