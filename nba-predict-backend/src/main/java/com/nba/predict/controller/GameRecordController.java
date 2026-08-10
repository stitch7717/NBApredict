package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.entity.GameRecord;
import com.nba.predict.service.GameRecordService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@Tag(name = "比赛记录接口")
@RestController
@RequestMapping("/game")
@RequiredArgsConstructor
public class GameRecordController {

    private final GameRecordService gameRecordService;

    @Operation(summary = "比赛列表")
    @GetMapping("/list")
    public Result<PageResult<GameRecord>> list(
            @Min(1) @RequestParam(defaultValue = "1") int page,
            @Min(1) @Max(100) @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String season,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate gameDate,
            @RequestParam(required = false) Long teamId) {
        Page<GameRecord> result = gameRecordService.listGames(page, size, season, gameDate, teamId);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "比赛详情")
    @GetMapping("/detail/{id}")
    public Result<GameRecord> detail(@PathVariable Long id) {
        return Result.success(gameRecordService.getGameDetail(id));
    }

    @Operation(summary = "球队对位战绩")
    @GetMapping("/battle")
    public Result<Object> battle(
            @RequestParam Long team1Id,
            @RequestParam Long team2Id,
            @RequestParam(required = false) String season) {
        return Result.success(gameRecordService.getBattleRecord(team1Id, team2Id, season));
    }
}
