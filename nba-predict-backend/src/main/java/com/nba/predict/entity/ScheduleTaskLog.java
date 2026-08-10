package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("schedule_task_log")
public class ScheduleTaskLog {

    @TableId(type = IdType.AUTO)
    private Long logId;

    private String taskName;

    private String taskGroup;

    private LocalDateTime executeTime;

    private LocalDateTime finishTime;

    private Integer duration;

    private String executeStatus;

    private String result;

    private String errorMsg;

    private Integer retryCount;

    private Integer maxRetry;

    private String triggerType;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
