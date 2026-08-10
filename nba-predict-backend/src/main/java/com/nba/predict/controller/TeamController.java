package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.dto.TeamPredictRequest;
import com.nba.predict.entity.Team;
import com.nba.predict.service.TeamService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@Tag(name = "球队接口")
@RestController
@RequestMapping("/team")
@RequiredArgsConstructor
@Validated
public class TeamController {

    private final TeamService teamService;

    @Operation(summary = "球队列表")
    @GetMapping("/list")
    public Result<PageResult<Team>> list(
            @Min(1) @RequestParam(defaultValue = "1") int page,
            @Min(1) @Max(100) @RequestParam(defaultValue = "30") int size,
            @RequestParam(required = false) String conference,
            @RequestParam(required = false) String defenseType,
            @RequestParam(required = false) String offenseType) {
        Page<Team> result = teamService.listTeams(page, size, conference, defenseType, offenseType);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "球队详情")
    @GetMapping("/detail/{id}")
    public Result<Team> detail(@PathVariable Long id) {
        return Result.success(teamService.getTeamDetail(id));
    }

    @Operation(summary = "球队对战预测")
    @PostMapping("/predict")
    public Result<Object> predict(@RequestBody TeamPredictRequest request) {
        return Result.success(teamService.predict(
                request.homeTeamId(), request.awayTeamId(),
                request.scene() != null ? request.scene() : "常规赛",
                request.useOdds() != null && request.useOdds()));
    }
}
