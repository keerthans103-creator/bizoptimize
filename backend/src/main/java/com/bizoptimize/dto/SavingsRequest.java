package com.bizoptimize.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;

public record SavingsRequest(
        @NotNull @PositiveOrZero Double hoursPerWeek, @NotNull @PositiveOrZero Double hourlyRate) {}
