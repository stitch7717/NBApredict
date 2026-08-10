package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.entity.PredictRecord;
import com.nba.predict.service.RecordService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@Tag(name = "预测记录接口")
@RestController
@RequestMapping("/record")
@RequiredArgsConstructor
public class RecordController {

    private final RecordService recordService;

    @Operation(summary = "预测记录列表")
    @GetMapping("/list")
    public Result<PageResult<PredictRecord>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String predictType,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate,
            @RequestParam(required = false) String status) {
        Page<PredictRecord> result = recordService.listRecords(page, size, predictType, startDate, endDate, status);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "预测记录详情")
    @GetMapping("/detail/{id}")
    public Result<PredictRecord> detail(@PathVariable Long id) {
        return Result.success(recordService.getRecordDetail(id));
    }

    @Operation(summary = "预测校准")
    @PostMapping("/calibrate")
    public Result<Void> calibrate(
            @RequestParam Long predictId,
            @RequestParam(required = false) Integer realPoints,
            @RequestParam(required = false) Double realFgPct,
            @RequestParam(required = false) Integer realHomeScore,
            @RequestParam(required = false) Integer realAwayScore) {
        recordService.calibrateRecord(predictId, realPoints, realFgPct, realHomeScore, realAwayScore);
        return Result.success();
    }
}
