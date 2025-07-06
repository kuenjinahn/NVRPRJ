/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

export const pages = (req, res) => {
  const maxPageSize = req.path === '/api/cameras' ? 50 : 6;
  const minPage = 1;

  let start = Number.parseInt(req.query.start); //for infinite scroll
  let page = Number.parseInt(req.query.page) || minPage;
  let pageSize = Number.parseInt(req.query.pageSize) || maxPageSize;

  // eslint-disable-next-line unicorn/prefer-number-properties
  start = !isNaN(start) ? start : null;
  const items = res.locals.items || [];
  const totalItems = res.locals.totalItems ?? items.length;
  const maxPage = Math.ceil(totalItems / pageSize);

  pageSize = pageSize > maxPageSize ? maxPageSize : pageSize;
  page = page < minPage ? minPage : page;

  /*if(page > maxPage && items.length){
    throw new Error('Page not found');
  }*/

  const startIndex = start !== null ? start : (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize - 1, totalItems - 1);

  const pagination = {
    currentPage: page,
    pageSize: pageSize,
    totalPages: maxPage,
    totalItems: totalItems,
    nextPage: page < maxPage ? `${req.path}?page=${page + 1}` : null,
    prevPage: page > 1 ? `${req.path}?page=${page - 1}` : null,
  };

  res.status(200).send({ pagination, result: items });
};
