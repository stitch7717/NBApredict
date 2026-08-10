package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.nba.predict.entity.SystemConfig;
import com.nba.predict.mapper.SystemConfigMapper;
import com.nba.predict.service.ConfigService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ConfigServiceImpl implements ConfigService {

    private final SystemConfigMapper systemConfigMapper;

    @Override
    public List<SystemConfig> listConfigs(String configGroup) {
        LambdaQueryWrapper<SystemConfig> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(configGroup)) {
            wrapper.eq(SystemConfig::getConfigGroup, configGroup);
        }
        wrapper.orderByAsc(SystemConfig::getConfigGroup, SystemConfig::getConfigKey);
        return systemConfigMapper.selectList(wrapper);
    }

    @Override
    public Map<String, String> getConfigMap(String configGroup) {
        List<SystemConfig> configs = listConfigs(configGroup);
        return configs.stream()
                .collect(Collectors.toMap(
                        SystemConfig::getConfigKey,
                        SystemConfig::getConfigValue,
                        (a, b) -> b,
                        LinkedHashMap::new));
    }

    @Override
    public String getConfigValue(String configGroup, String configKey) {
        SystemConfig config = systemConfigMapper.selectOne(
                new LambdaQueryWrapper<SystemConfig>()
                        .eq(SystemConfig::getConfigGroup, configGroup)
                        .eq(SystemConfig::getConfigKey, configKey));
        return config != null ? config.getConfigValue() : null;
    }

    @Override
    public void updateConfig(String configGroup, String configKey, String configValue) {
        LambdaUpdateWrapper<SystemConfig> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(SystemConfig::getConfigGroup, configGroup)
                     .eq(SystemConfig::getConfigKey, configKey)
                     .set(SystemConfig::getConfigValue, configValue);
        int updated = systemConfigMapper.update(null, updateWrapper);
        if (updated > 0) {
            log.info("配置已更新: {}.{} = {}", configGroup, configKey, configValue);
        }
    }

    @Override
    public Map<String, Object> getFullConfig() {
        List<SystemConfig> allConfigs = systemConfigMapper.selectList(null);
        Map<String, Object> result = new LinkedHashMap<>();

        Map<String, List<SystemConfig>> grouped = allConfigs.stream()
                .collect(Collectors.groupingBy(SystemConfig::getConfigGroup, LinkedHashMap::new, Collectors.toList()));

        for (Map.Entry<String, List<SystemConfig>> entry : grouped.entrySet()) {
            Map<String, String> groupMap = entry.getValue().stream()
                    .collect(Collectors.toMap(
                            SystemConfig::getConfigKey,
                            SystemConfig::getConfigValue,
                            (a, b) -> b,
                            LinkedHashMap::new));
            result.put(entry.getKey(), groupMap);
        }

        return result;
    }
}
