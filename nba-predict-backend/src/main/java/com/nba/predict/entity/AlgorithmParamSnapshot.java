package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("algorithm_param_snapshot")
public class AlgorithmParamSnapshot {

    @TableId(type = IdType.AUTO)
    private Long snapshotId;

    private String version;

    private String paramJson;

    private String description;

    private BigDecimal maeScore;

    private Integer isCurrent;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
