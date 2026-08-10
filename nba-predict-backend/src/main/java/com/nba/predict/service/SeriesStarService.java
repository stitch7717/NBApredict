package com.nba.predict.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.nba.predict.entity.SeriesStar;

public interface SeriesStarService {

    Page<SeriesStar> listStars(int page, int size, Long teamId, String season);

    SeriesStar getStarDetail(Long starId);

    Object getSeasonReview(int page, int size, String season, Long teamId);
}
