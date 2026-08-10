package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.entity.OddsData;
import com.nba.predict.service.OddsService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@Tag(name = "赔率接口")
@RestController
@RequestMapping("/odds")
@RequiredArgsConstructor
public class OddsController {

    private final OddsService oddsService;

    @Operation(summary = "赔率列表")
    @GetMapping("/list")
    public Result<PageResult<OddsData>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) Long homeTeamId,
            @RequestParam(required = false) Long awayTeamId,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate gameDate,
            @RequestParam(required = false) Long sourceId) {
        Page<OddsData> result = oddsService.listOdds(page, size, homeTeamId, awayTeamId, gameDate, sourceId);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "赔率详情")
    @GetMapping("/detail/{id}")
    public Result<OddsData> detail(@PathVariable Long id) {
        return Result.success(oddsService.getOddsDetail(id));
    }

    @Operation(summary = "赔率换算")
    @PostMapping("/convert")
    public Result<Object> convert(@RequestParam Long oddsId) {
        return Result.success(oddsService.convertOdds(oddsId));
    }

    @Operation(summary = "手动采集赔率")
    @PostMapping("/collect")
    public Result<Object> collect(
            @RequestParam Long sourceId,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate) {
        return Result.success(oddsService.collectOdds(sourceId, startDate, endDate));
    }

    @Operation(summary = "赔率回测")
    @PostMapping("/backtest")
    public Result<Object> backtest(
            @RequestParam String season,
            @RequestParam(required = false) Long sourceId) {
        return Result.success(oddsService.backtestOdds(season, sourceId));
    }
}
