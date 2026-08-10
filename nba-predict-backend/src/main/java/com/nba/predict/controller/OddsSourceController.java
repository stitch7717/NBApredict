package com.nba.predict.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.PageResult;
import com.nba.predict.common.Result;
import com.nba.predict.entity.OddsSource;
import com.nba.predict.service.OddsSourceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "数据源接口")
@RestController
@RequestMapping("/datasource")
@RequiredArgsConstructor
@Validated
public class OddsSourceController {

    private final OddsSourceService oddsSourceService;

    @Operation(summary = "数据源列表（全部）")
    @GetMapping("/list")
    public Result<List<OddsSource>> listAll() {
        return Result.success(oddsSourceService.listAllSources());
    }

    @Operation(summary = "数据源列表（分页）")
    @GetMapping("/page")
    public Result<PageResult<OddsSource>> list(
            @Min(1) @RequestParam(defaultValue = "1") int page,
            @Min(1) @Max(100) @RequestParam(defaultValue = "10") int size) {
        Page<OddsSource> result = oddsSourceService.listSources(page, size);
        return Result.success(PageResult.of(result.getTotal(), page, size, result.getRecords()));
    }

    @Operation(summary = "数据源详情")
    @GetMapping("/detail/{id}")
    public Result<OddsSource> detail(@PathVariable Long id) {
        return Result.success(oddsSourceService.getSourceDetail(id));
    }

    @Operation(summary = "数据源评估")
    @PostMapping("/evaluate")
    public Result<Object> evaluate() {
        return Result.success(oddsSourceService.evaluateSources());
    }

    @Operation(summary = "手动切换主数据源")
    @PostMapping("/switch")
    public Result<Void> switchSource(@RequestParam Long sourceId) {
        oddsSourceService.switchPrimarySource(sourceId);
        return Result.success();
    }
}
