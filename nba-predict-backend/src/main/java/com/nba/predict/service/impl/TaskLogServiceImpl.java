package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.GameRecord;
import com.nba.predict.entity.ScheduleTaskLog;
import com.nba.predict.mapper.GameRecordMapper;
import com.nba.predict.mapper.ScheduleTaskLogMapper;
import com.nba.predict.service.TaskLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 任务日志服务实现
 */
@Service
@RequiredArgsConstructor
public class TaskLogServiceImpl implements TaskLogService {

    /** 状态汇总里每个任务只保留最近一次，扫描的日志条数上限 */
    private static final int STATUS_SCAN_LIMIT = 200;

    private final ScheduleTaskLogMapper taskLogMapper;
    private final GameRecordMapper gameRecordMapper;

    @Override
    public Page<ScheduleTaskLog> listLogs(int page, int size, String taskName, String status) {
        Page<ScheduleTaskLog> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<ScheduleTaskLog> wrapper = new LambdaQueryWrapper<>();
        if (taskName != null) {
            wrapper.eq(ScheduleTaskLog::getTaskName, taskName);
        }
        if (status != null) {
            wrapper.eq(ScheduleTaskLog::getExecuteStatus, status);
        }
        wrapper.orderByDesc(ScheduleTaskLog::getExecuteTime);
        return taskLogMapper.selectPage(pageParam, wrapper);
    }

    @Override
    public Map<String, Object> statusSummary() {
        Map<String, Object> summary = new LinkedHashMap<>();

        // 数据新鲜度：最新一场已结束比赛的日期
        GameRecord latestGame = gameRecordMapper.selectOne(
                new LambdaQueryWrapper<GameRecord>()
                        .eq(GameRecord::getStatus, "FINISHED")
                        .orderByDesc(GameRecord::getGameDate)
                        .last("LIMIT 1"));
        summary.put("latestGameDate", latestGame != null ? latestGame.getGameDate() : null);
        summary.put("gameCount", gameRecordMapper.selectCount(null));

        // 每个任务取最近一次执行记录
        List<ScheduleTaskLog> logs = taskLogMapper.selectList(
                new LambdaQueryWrapper<ScheduleTaskLog>()
                        .orderByDesc(ScheduleTaskLog::getExecuteTime)
                        .last("LIMIT " + STATUS_SCAN_LIMIT));
        Map<String, ScheduleTaskLog> latestByTask = new LinkedHashMap<>();
        for (ScheduleTaskLog log : logs) {
            latestByTask.putIfAbsent(log.getTaskName(), log);
        }
        summary.put("tasks", latestByTask.values());
        return summary;
    }
}
