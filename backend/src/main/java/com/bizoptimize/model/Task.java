package com.bizoptimize.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "tasks")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Task {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "workflow_id", nullable = false)
    @JsonIgnore
    private Workflow workflow;

    @Lob
    @Column(name = "task_text", nullable = false)
    private String taskText;

    @Lob
    private String hint;

    @Column(nullable = false)
    private Integer score;

    @Lob
    private String explanation;

    /** JSON-serialized feature dict from the ML service, stored as text for portability. */
    @Lob
    @Column(name = "features_json")
    private String featuresJson;

    /** JSON-serialized list of RAG automation matches (empty array if score < 70). */
    @Lob
    @Column(name = "automation_json")
    private String automationJson;

    @Column(name = "hours_per_week")
    private Double hoursPerWeek;

    @Column(name = "hourly_rate")
    private Double hourlyRate;

    @Column(name = "estimated_annual_savings")
    private Double estimatedAnnualSavings;

    /** "AUTOMATE" or "SKIP" from the Feed swipe deck, null if never decided on. */
    @Column(name = "automation_decision")
    private String automationDecision;
}
