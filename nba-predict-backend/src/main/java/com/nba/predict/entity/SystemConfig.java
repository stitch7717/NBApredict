package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("system_config")
public class SystemConfig {

    @TableId(type = IdType.AUTO)
    private Long configId;

    private String configGroup;

    private String configKey;

    private String configValue;

    private String configType;

    private String description;

    private BigDecimal minValue;

    private BigDecimal maxValue;

    private String defaultValue;

    private Integer isSystem;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
