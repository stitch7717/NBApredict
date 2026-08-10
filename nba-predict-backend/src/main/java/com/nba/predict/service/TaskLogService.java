package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.ScheduleTaskLog;

/**
 * 任务日志服务接口
 */
public interface TaskLogService {

    Page<ScheduleTaskLog> listLogs(int page, int size, String taskName, String status);
}
