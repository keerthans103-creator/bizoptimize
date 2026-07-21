package com.bizoptimize.controller;

import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.notNullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class WorkflowControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    private static final String WORKFLOW_PAYLOAD =
            """
            {
              "title": "Weekly report workflow",
              "rawText": "Pull sales numbers and email a report every Monday.",
              "tasks": [
                {
                  "task_text": "Pull sales numbers and format them into a report.",
                  "hint": "recurring, tool-integrated",
                  "score": 82,
                  "explanation": "Driven by repetitive, structured-data language.",
                  "features": {"repetitiveness": 0.1, "tool_mention": 0.05},
                  "automation": [{"id": "reporting-weekly-sales", "title": "Automated weekly sales report", "category": "reporting", "similarity": 0.4, "instructions": "use cron + pandas", "tags": ["sql", "pandas"]}],
                  "automation_decision": "AUTOMATE"
                }
              ]
            }
            """;

    private String registerAndGetToken(String email) throws Exception {
        String payload = objectMapper.writeValueAsString(new java.util.HashMap<>() {
            {
                put("email", email);
                put("password", "supersecret123");
            }
        });
        String response =
                mockMvc
                        .perform(post("/api/auth/register").contentType(MediaType.APPLICATION_JSON).content(payload))
                        .andExpect(status().isOk())
                        .andReturn()
                        .getResponse()
                        .getContentAsString();
        return objectMapper.readTree(response).get("token").asText();
    }

    private String token;

    @BeforeEach
    void setUp() throws Exception {
        token = registerAndGetToken("workflow-owner-" + System.nanoTime() + "@example.com");
    }

    @Test
    void savingThenListingThenFetchingReturnsTheSameWorkflow() throws Exception {
        String saveResponse =
                mockMvc
                        .perform(
                                post("/api/workflows")
                                        .header("Authorization", "Bearer " + token)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(WORKFLOW_PAYLOAD))
                        .andExpect(status().isCreated())
                        .andExpect(jsonPath("$.id").value(notNullValue()))
                        .andExpect(jsonPath("$.title").value("Weekly report workflow"))
                        .andExpect(jsonPath("$.tasks", hasSize(1)))
                        .andExpect(jsonPath("$.tasks[0].score").value(82))
                        .andExpect(jsonPath("$.tasks[0].taskText").value("Pull sales numbers and format them into a report."))
                        .andExpect(jsonPath("$.tasks[0].automationDecision").value("AUTOMATE"))
                        .andReturn()
                        .getResponse()
                        .getContentAsString();

        long workflowId = objectMapper.readTree(saveResponse).get("id").asLong();

        mockMvc
                .perform(get("/api/workflows").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id").value(workflowId));

        mockMvc
                .perform(get("/api/workflows/" + workflowId).header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Weekly report workflow"))
                .andExpect(jsonPath("$.tasks[0].automation[0].id").value("reporting-weekly-sales"))
                .andExpect(jsonPath("$.tasks[0].automationDecision").value("AUTOMATE"));
    }

    @Test
    void listingWithoutAuthIsRejected() throws Exception {
        // No custom AuthenticationEntryPoint is configured, so Spring Security's
        // default for a missing/invalid JWT here is 403, not 401 -- either is a
        // reasonable convention, this just documents which one this app actually uses.
        mockMvc.perform(get("/api/workflows")).andExpect(status().isForbidden());
    }

    @Test
    void anotherUsersWorkflowIsNotFoundNotForbidden() throws Exception {
        String ownerToken = registerAndGetToken("owner-" + System.nanoTime() + "@example.com");
        String saveResponse =
                mockMvc
                        .perform(
                                post("/api/workflows")
                                        .header("Authorization", "Bearer " + ownerToken)
                                        .contentType(MediaType.APPLICATION_JSON)
                                        .content(WORKFLOW_PAYLOAD))
                        .andExpect(status().isCreated())
                        .andReturn()
                        .getResponse()
                        .getContentAsString();
        long workflowId = objectMapper.readTree(saveResponse).get("id").asLong();

        String otherToken = registerAndGetToken("other-" + System.nanoTime() + "@example.com");
        mockMvc
                .perform(get("/api/workflows/" + workflowId).header("Authorization", "Bearer " + otherToken))
                .andExpect(status().isNotFound());
    }
}
