package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("battle_record")
public class BattleRecord {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long team1Id;

    private Long team2Id;

    private String season;

    private Integer totalGames;

    private Integer team1Wins;

    private Integer team2Wins;

    private BigDecimal team1AvgScore;

    private BigDecimal team2AvgScore;

    private BigDecimal avgScoreDiff;

    private Integer team1HomeWins;

    private Integer team1AwayWins;

    private LocalDate lastGameDate;

    private String lastGameScore;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
