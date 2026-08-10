package com.nba.predict.controller;

import com.nba.predict.common.Result;
import com.nba.predict.entity.SystemConfig;
import com.nba.predict.service.ConfigService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "系统配置接口")
@RestController
@RequestMapping("/config")
@RequiredArgsConstructor
public class ConfigController {

    private final ConfigService configService;

    @Operation(summary = "获取全部配置")
    @GetMapping("/get")
    public Result<Map<String, Object>> getFullConfig() {
        return Result.success(configService.getFullConfig());
    }

    @Operation(summary = "按分组获取配置")
    @GetMapping("/group/{group}")
    public Result<List<SystemConfig>> getByGroup(@PathVariable String group) {
        return Result.success(configService.listConfigs(group));
    }

    @Operation(summary = "更新配置")
    @PostMapping("/update")
    public Result<Void> update(
            @RequestParam String configGroup,
            @RequestParam String configKey,
            @RequestParam String configValue) {
        configService.updateConfig(configGroup, configKey, configValue);
        return Result.success();
    }
}
