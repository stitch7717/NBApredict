package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.entity.SeriesStar;
import com.nba.predict.service.SeriesStarService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

@Tag(name = "系列赛接口")
@RestController
@RequestMapping("/series")
@RequiredArgsConstructor
@Validated
public class SeriesStarController {

    private final SeriesStarService seriesStarService;

    @Operation(summary = "系列赛之星列表")
    @GetMapping("/star")
    public Result<PageResult<SeriesStar>> listStars(
            @Min(1) @RequestParam(defaultValue = "1") int page,
            @Min(1) @Max(100) @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) Long teamId,
            @RequestParam(required = false) String season) {
        Page<SeriesStar> result = seriesStarService.listStars(page, size, teamId, season);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "系列赛之星详情")
    @GetMapping("/star/{id}")
    public Result<SeriesStar> starDetail(@PathVariable Long id) {
        return Result.success(seriesStarService.getStarDetail(id));
    }

    @Operation(summary = "全赛季复盘")
    @GetMapping("/review")
    public Result<Object> review(
            @Min(1) @RequestParam(defaultValue = "1") int page,
            @Min(1) @Max(100) @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String season,
            @RequestParam(required = false) Long teamId) {
        return Result.success(seriesStarService.getSeasonReview(page, size, season, teamId));
    }
}
