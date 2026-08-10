package com.nba.predict.scheduler;

import com.nba.predict.entity.ScheduleTaskLog;
import com.nba.predict.mapper.ScheduleTaskLogMapper;
import com.nba.predict.util.HttpUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
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
public class DataUpdateTask {

    private final HttpUtil httpUtil;
    private final ObjectMapper objectMapper;
    private final ScheduleTaskLogMapper taskLogMapper;

    /**
     * 每日凌晨3点：更新球员/球队基础数据
     */
    @Scheduled(cron = "0 0 3 * * ?")
    public void updatePlayerAndTeamData() {
        String taskName = "update_player_team_data";
        ScheduleTaskLog taskLog = startTask(taskName, "DATA_UPDATE");

        try {
            Map<String, Object> request = new HashMap<>();
            request.put("type", "all");
            String response = httpUtil.post("/algorithm/data/update", request);

            finishTask(taskLog, "SUCCESS", response);
            log.info("球员/球队数据更新完成");
        } catch (Exception e) {
            finishTask(taskLog, "FAIL", e.getMessage());
            log.error("球员/球队数据更新失败: {}", e.getMessage());
        }
    }

    /**
     * 每日凌晨1点：更新箭头人物对位数据
     */
    @Scheduled(cron = "0 0 1 * * ?")
    public void updateMatchupData() {
        String taskName = "update_matchup_data";
        ScheduleTaskLog taskLog = startTask(taskName, "DATA_UPDATE");

        try {
            Map<String, Object> request = new HashMap<>();
            request.put("type", "matchup");
            String response = httpUtil.post("/algorithm/data/update", request);

            finishTask(taskLog, "SUCCESS", response);
            log.info("对位数据更新完成");
        } catch (Exception e) {
            finishTask(taskLog, "FAIL", e.getMessage());
            log.error("对位数据更新失败: {}", e.getMessage());
        }
    }

    /**
     * 每30分钟：更新实时赔率数据
     */
    @Scheduled(cron = "0 */30 * * * ?")
    public void updateOddsData() {
        String taskName = "update_odds_data";
        ScheduleTaskLog taskLog = startTask(taskName, "ODDS_UPDATE");

        try {
            Map<String, Object> request = new HashMap<>();
            request.put("type", "odds");
            String response = httpUtil.post("/algorithm/odds/collect", request);

            finishTask(taskLog, "SUCCESS", response);
            log.info("赔率数据更新完成");
        } catch (Exception e) {
            finishTask(taskLog, "FAIL", e.getMessage());
            log.error("赔率数据更新失败: {}", e.getMessage());
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
