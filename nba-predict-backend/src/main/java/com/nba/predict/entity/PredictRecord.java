package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("predict_record")
public class PredictRecord {

    @TableId(type = IdType.AUTO)
    private Long predictId;

    private String predictType;

    private Long gameId;

    private LocalDate gameDate;

    private Long playerId;

    private Long opponentPlayerId;

    private Long homeTeamId;

    private Long awayTeamId;

    private String scene;

    private Integer useOdds;

    private Long oddsSourceId;

    private Double predictPointsLow;

    private Double predictPointsMid;

    private Double predictPointsHigh;

    private Double predictFgPct;

    private Integer predictHomeScore;

    private Integer predictAwayScore;

    private Integer predictTotalScore;

    private Integer predictScoreDiff;

    private Integer predictHomeScoreOdds;

    private Integer predictAwayScoreOdds;

    private Integer predictTotalScoreOdds;

    private Integer predictScoreDiffOdds;

    private Double allStarCoeff;

    private Double veteranCoeff;

    private Double injuryCoeff;

    private Double clutchCoeff;

    private Double homeCoeff;

    private Double fatigueCoeff;

    private Double oddsCoeff;

    private Double totalCoeff;

    private Integer realPoints;

    private Double realFgPct;

    private Integer realHomeScore;

    private Integer realAwayScore;

    private Integer realTotalScore;

    private Integer realScoreDiff;

    private Double errorPoints;

    private Integer errorTotal;

    private Integer errorDiff;

    private String status;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
