package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("game_record")
public class GameRecord {

    @TableId(type = IdType.AUTO)
    private Long gameId;

    private String nbaGameId;

    private String season;

    private LocalDate gameDate;

    private String gameType;

    private Long homeTeamId;

    private Long awayTeamId;

    private Integer homeScore;

    private Integer awayScore;

    private Integer homeQ1Score;

    private Integer homeQ2Score;

    private Integer homeQ3Score;

    private Integer homeQ4Score;

    private Integer awayQ1Score;

    private Integer awayQ2Score;

    private Integer awayQ3Score;

    private Integer awayQ4Score;

    private Integer overtime;

    private Integer homeWin;

    private Integer scoreDiff;

    private Integer totalScore;

    private Integer isPlayoff;

    private String playoffRound;

    private Long seriesId;

    private String status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
