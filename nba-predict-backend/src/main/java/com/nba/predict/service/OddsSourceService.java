package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.OddsSource;

import java.util.List;

public interface OddsSourceService {

    List<OddsSource> listAllSources();

    Page<OddsSource> listSources(int page, int size);

    OddsSource getSourceDetail(Long sourceId);

    Object evaluateSources();

    void switchPrimarySource(Long sourceId);
}
