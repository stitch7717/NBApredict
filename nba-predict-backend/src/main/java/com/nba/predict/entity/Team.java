package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("team")
public class Team {

    @TableId(type = IdType.AUTO)
    private Long teamId;

    private String nbaId;

    private String teamName;

    private String teamNameEn;

    private String abbreviation;

    private String conference;

    private String division;

    private String city;

    private String arena;

    private String defenseType;

    private String offenseType;

    private Integer defenseCluster;

    private Integer offenseCluster;

    private String strengthLevel;

    private Double strengthScore;

    private Integer tagResilience;

    private Integer tagSlowStart;

    private Integer tagCoreDepend;

    private Double homeWinRate;

    private Double awayWinRate;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
