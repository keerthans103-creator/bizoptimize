package com.bizoptimize.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Serializes the ML service's feature/automation payloads to/from the TEXT columns they're stored in. */
@Component
public class JsonConverter {

    private final ObjectMapper mapper = new ObjectMapper();

    public String writeMap(Map<String, Object> map) {
        try {
            return mapper.writeValueAsString(map == null ? Map.of() : map);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Failed to serialize feature map", e);
        }
    }

    public String writeList(List<Map<String, Object>> list) {
        try {
            return mapper.writeValueAsString(list == null ? List.of() : list);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("Failed to serialize automation list", e);
        }
    }

    public Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) return Map.of();
        try {
            return mapper.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (JsonProcessingException e) {
            return Map.of();
        }
    }

    public List<Map<String, Object>> readList(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            return mapper.readValue(json, new TypeReference<List<Map<String, Object>>>() {});
        } catch (JsonProcessingException e) {
            return List.of();
        }
    }
}
