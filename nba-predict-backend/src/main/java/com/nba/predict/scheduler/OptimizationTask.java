package com.nba.predict.scheduler;

import com.nba.predict.entity.ScheduleTaskLog;
import com.nba.predict.mapper.ScheduleTaskLogMapper;
import com.nba.predict.util.HttpUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class OptimizationTask {

    private final HttpUtil httpUtil;
    private final ScheduleTaskLogMapper taskLogMapper;

    /**
     * 每周一凌晨4点：执行权重自动优化
     */
    @Scheduled(cron = "0 0 4 ? * MON")
    public void runWeightOptimization() {
        String taskName = "weight_optimization";
        ScheduleTaskLog taskLog = startTask(taskName, "OPTIMIZATION");

        try {
            Map<String, Object> request = new HashMap<>();
            request.put("type", "weight");
            String response = httpUtil.post("/algorithm/config/optimize", request);

            finishTask(taskLog, "SUCCESS", response);
            log.info("权重优化完成");
        } catch (Exception e) {
            finishTask(taskLog, "FAIL", e.getMessage());
            log.error("权重优化失败: {}", e.getMessage());
        }
    }

    /**
     * 每周一凌晨5点：执行数据源评估
     */
    @Scheduled(cron = "0 0 5 ? * MON")
    public void runDataSourceEvaluation() {
        String taskName = "datasource_evaluation";
        ScheduleTaskLog taskLog = startTask(taskName, "OPTIMIZATION");

        try {
            String response = httpUtil.get("/algorithm/datasource/evaluate");

            finishTask(taskLog, "SUCCESS", response);
            log.info("数据源评估完成");
        } catch (Exception e) {
            finishTask(taskLog, "FAIL", e.getMessage());
            log.error("数据源评估失败: {}", e.getMessage());
        }
    }

    private ScheduleTaskLog startTask(String taskName, String taskGroup) {
        ScheduleTaskLog taskLog = new ScheduleTaskLog();
        taskLog.setTaskName(taskName);
        taskLog.setTaskGroup(taskGroup);
        taskLog.setExecuteTime(LocalDateTime.now());
        taskLog.setExecuteStatus("RUNNING");
        taskLog.setTriggerType("SCHEDULED");
        taskLog.setRetryCount(0);
        taskLog.setMaxRetry(1);
        taskLogMapper.insert(taskLog);
        return taskLog;
    }

    private void finishTask(ScheduleTaskLog taskLog, String status, String result) {
        taskLog.setFinishTime(LocalDateTime.now());
        taskLog.setDuration((int) (java.time.Duration.between(
                taskLog.getExecuteTime(), taskLog.getFinishTime()).getSeconds()));
        taskLog.setExecuteStatus(status);
        if ("FAIL".equals(status)) {
            taskLog.setErrorMsg(result);
        } else {
            taskLog.setResult(result);
        }
        taskLogMapper.updateById(taskLog);
    }
}
