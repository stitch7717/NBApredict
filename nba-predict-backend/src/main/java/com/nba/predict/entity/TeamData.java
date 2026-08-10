package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("team_data")
public class TeamData {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long teamId;

    private String season;

    private Integer wins;

    private Integer losses;

    private BigDecimal winPercentage;

    private Integer homeWins;

    private Integer homeLosses;

    private Integer awayWins;

    private Integer awayLosses;

    private BigDecimal pointsPerGame;

    private BigDecimal assistsPerGame;

    private BigDecimal reboundsPerGame;

    private BigDecimal offensiveRebounds;

    private BigDecimal turnoversPerGame;

    private BigDecimal fgPercentage;

    private BigDecimal threePercentage;

    private BigDecimal ftPercentage;

    private BigDecimal pace;

    private BigDecimal offensiveRating;

    private BigDecimal opponentPoints;

    private BigDecimal opponentFgPercentage;

    private BigDecimal opponentThreePct;

    private BigDecimal defensiveRating;

    private BigDecimal stealsPerGame;

    private BigDecimal blocksPerGame;

    private BigDecimal fastBreakPoints;

    private BigDecimal pointsInPaint;

    private BigDecimal secondChancePoints;

    private BigDecimal benchPoints;

    private BigDecimal pointsStd;

    private BigDecimal pointsCv;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
