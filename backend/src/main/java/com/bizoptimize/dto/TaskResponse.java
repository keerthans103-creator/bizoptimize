package com.bizoptimize.dto;

import java.util.List;
import java.util.Map;

public record TaskResponse(
        Long id,
        String taskText,
        String hint,
        Integer score,
        String explanation,
        Map<String, Object> features,
        List<Map<String, Object>> automation,
        Double hoursPerWeek,
        Double hourlyRate,
        Double estimatedAnnualSavings,
        String automationDecision) {}
