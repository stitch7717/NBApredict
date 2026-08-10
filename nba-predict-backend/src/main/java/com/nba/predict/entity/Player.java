package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("player")
public class Player {

    @TableId(type = IdType.AUTO)
    private Long playerId;

    private String nbaId;

    private String playerName;

    private String playerNameEn;

    private String position;

    private Integer jerseyNumber;

    private Long teamId;

    private LocalDate birthDate;

    private Integer age;

    private Double height;

    private Double weight;

    private Integer draftYear;

    private Integer draftRound;

    private Integer draftPick;

    private Integer experience;

    private Integer allStarCount;

    private Integer allStarLast;

    private String injuryStatus;

    private String injuryType;

    private LocalDate injuryDate;

    private String playerType;

    private Integer clusterId;

    private String clusterName;

    private Integer status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
