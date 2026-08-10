package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.dto.PlayerPredictRequest;
import com.nba.predict.entity.Player;
import com.nba.predict.service.PlayerService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@Tag(name = "球员接口")
@RestController
@RequestMapping("/player")
@RequiredArgsConstructor
@Validated
public class PlayerController {

    private final PlayerService playerService;

    @Operation(summary = "球员列表")
    @GetMapping("/list")
    public Result<PageResult<Player>> list(
            @Min(1) @RequestParam(defaultValue = "1") int page,
            @Min(1) @Max(100) @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String position,
            @RequestParam(required = false) Integer teamId) {
        Page<Player> result = playerService.listPlayers(page, size, keyword, position, teamId);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "球员详情")
    @GetMapping("/detail/{id}")
    public Result<Player> detail(@PathVariable Long id) {
        return Result.success(playerService.getPlayerDetail(id));
    }

    @Operation(summary = "球员预测")
    @PostMapping("/predict")
    public Result<Object> predict(@RequestBody PlayerPredictRequest request) {
        return Result.success(playerService.predict(
                request.playerId(), request.opponentPlayerId(),
                request.scene() != null ? request.scene() : "常规赛",
                request.homeAway() != null ? request.homeAway() : "home"));
    }
}
