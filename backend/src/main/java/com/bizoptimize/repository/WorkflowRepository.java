package com.bizoptimize.repository;

import com.bizoptimize.model.Workflow;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WorkflowRepository extends JpaRepository<Workflow, Long> {
    List<Workflow> findByUserIdOrderByCreatedAtDesc(Long userId);
}
