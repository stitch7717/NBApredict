package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.ScheduleTaskLog;
import com.nba.predict.mapper.ScheduleTaskLogMapper;
import com.nba.predict.service.TaskLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/**
 * 任务日志服务实现
 */
@Service
@RequiredArgsConstructor
public class TaskLogServiceImpl implements TaskLogService {

    private final ScheduleTaskLogMapper taskLogMapper;

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
}
