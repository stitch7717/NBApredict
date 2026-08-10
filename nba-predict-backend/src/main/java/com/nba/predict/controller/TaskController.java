package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.entity.ScheduleTaskLog;
import com.nba.predict.scheduler.DataUpdateTask;
import com.nba.predict.scheduler.OptimizationTask;
import com.nba.predict.service.TaskLogService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@Tag(name = "定时任务接口")
@RestController
@RequestMapping("/task")
@RequiredArgsConstructor
public class TaskController {

    private final TaskLogService taskLogService;
    private final DataUpdateTask dataUpdateTask;
    private final OptimizationTask optimizationTask;

    @Operation(summary = "任务执行日志")
    @GetMapping("/log")
    public Result<PageResult<ScheduleTaskLog>> listLogs(
            @Min(1) @RequestParam(defaultValue = "1") int page,
            @Min(1) @Max(100) @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String taskName,
            @RequestParam(required = false) String status) {
        var result = taskLogService.listLogs(page, size, taskName, status);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "手动触发数据更新")
    @PostMapping("/update-data")
    public Result<String> triggerDataUpdate() {
        dataUpdateTask.updatePlayerAndTeamData();
        return Result.success("数据更新任务已触发");
    }

    @Operation(summary = "手动触发赔率更新")
    @PostMapping("/update-odds")
    public Result<String> triggerOddsUpdate() {
        dataUpdateTask.updateOddsData();
        return Result.success("赔率更新任务已触发");
    }

    @Operation(summary = "手动触发权重优化")
    @PostMapping("/optimize")
    public Result<String> triggerOptimization() {
        optimizationTask.runWeightOptimization();
        return Result.success("权重优化任务已触发");
    }

    @Operation(summary = "手动触发数据源评估")
    @PostMapping("/evaluate")
    public Result<String> triggerEvaluation() {
        optimizationTask.runDataSourceEvaluation();
        return Result.success("数据源评估任务已触发");
    }
}
