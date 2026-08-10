package com.nba.predict.service;

import com.nba.predict.entity.SystemConfig;

import java.util.List;
import java.util.Map;

public interface ConfigService {

    List<SystemConfig> listConfigs(String configGroup);

    Map<String, String> getConfigMap(String configGroup);

    String getConfigValue(String configGroup, String configKey);

    void updateConfig(String configGroup, String configKey, String configValue);

    Map<String, Object> getFullConfig();
}
