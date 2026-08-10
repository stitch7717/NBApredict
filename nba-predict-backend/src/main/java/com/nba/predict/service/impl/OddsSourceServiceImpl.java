package com.nba.predict.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.common.ResultCode;
import com.nba.predict.entity.OddsSource;
import com.nba.predict.exception.BusinessException;
import com.nba.predict.mapper.OddsSourceMapper;
import com.nba.predict.service.OddsSourceService;
import com.nba.predict.util.HttpUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class OddsSourceServiceImpl implements OddsSourceService {

    private final OddsSourceMapper oddsSourceMapper;
    private final HttpUtil httpUtil;
    private final ObjectMapper objectMapper;

    @Override
    public List<OddsSource> listAllSources() {
        return oddsSourceMapper.selectList(
                new LambdaQueryWrapper<OddsSource>().orderByAsc(OddsSource::getPriority));
    }

    @Override
    public Page<OddsSource> listSources(int page, int size) {
        Page<OddsSource> pageParam = new Page<>(page, size);
        LambdaQueryWrapper<OddsSource> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByAsc(OddsSource::getPriority);
        return oddsSourceMapper.selectPage(pageParam, wrapper);
    }

    @Override
    public OddsSource getSourceDetail(Long sourceId) {
        OddsSource source = oddsSourceMapper.selectById(sourceId);
        if (source == null) {
            throw new BusinessException(ResultCode.ODDS_SOURCE_NOT_FOUND);
        }
        return source;
    }

    @Override
    public Object evaluateSources() {
        try {
            String response = httpUtil.get("/algorithm/datasource/evaluate");
            return objectMapper.readValue(response, Map.class);
        } catch (Exception e) {
            log.error("数据源评估失败: {}", e.getMessage());
            throw new BusinessException(ResultCode.ALGORITHM_ERROR);
        }
    }

    @Override
    @Transactional
    public void switchPrimarySource(Long sourceId) {
        OddsSource newPrimary = getSourceDetail(sourceId);

        // 取消当前主数据源
        OddsSource currentPrimary = oddsSourceMapper.selectOne(
                new LambdaQueryWrapper<OddsSource>().eq(OddsSource::getIsPrimary, 1));
        if (currentPrimary != null) {
            currentPrimary.setIsPrimary(0);
            oddsSourceMapper.updateById(currentPrimary);
        }

        // 设置新的主数据源
        newPrimary.setIsPrimary(1);
        newPrimary.setPriority(0);
        oddsSourceMapper.updateById(newPrimary);

        log.info("主数据源已切换为: {}", newPrimary.getSourceName());
    }
}
