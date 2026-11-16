package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.ScheduleTaskLog;

import java.util.Map;

/**
 * 任务日志服务接口
 */
public interface TaskLogService {

    Page<ScheduleTaskLog> listLogs(int page, int size, String taskName, String status);

    /**
     * 数据新鲜度与各定时任务最近执行情况，供前端展示"数据更新至 X"。
     */
    Map<String, Object> statusSummary();
}
