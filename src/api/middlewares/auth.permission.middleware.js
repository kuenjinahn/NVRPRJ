/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

export const minimumPermissionLevelRequired = (required_permission_level) => (req, res, next) => next();

export const onlySameUserOrAdminCanDoThisAction = (req, res, next) => {
  let user_permission_level = req.jwt.permissionLevel || [];
  let userId = req.jwt.userId;

  console.log('[PermissionMiddleware] PATCH /api/users/:userId');
  console.log('  req.jwt.userId:', userId);
  console.log('  req.params:', req.params);
  console.log('  user_permission_level:', user_permission_level);

  if (req.params && req.params.name && userId === req.params.name) {
    console.log('  권한: 본인');
    return next();
  } else {
    const isAdmin = user_permission_level.includes('users:edit') || user_permission_level.includes('admin');
    console.log('  권한: 관리자 여부', isAdmin);
    return isAdmin
      ? next()
      : res.status(403).send({
        statusCode: 403,
        message: 'Forbidden',
      });
  }
};

export const onlySameUserOrMasterCanDoThisAction = (req, res, next) => next();

export const onlyMasterCanDoThisAction = (req, res, next) => next();

export const masterCantDoThisAction = (req, res, next) => {
  let user_permission_level = req.jwt.permissionLevel || [];

  return !user_permission_level.includes('admin')
    ? next()
    : res.status(403).send({
      statusCode: 403,
      message: 'Forbidden',
    });
};

export const sameUserCantDoThisAction = (req, res, next) => {
  let userId = req.jwt.userId;
  console.log('[PermissionMiddleware] sameUserCantDoThisAction');
  console.log('  req.jwt.userId:', userId);
  console.log('  req.params:', req.params);
  return req.params.name !== userId
    ? next()
    : res.status(403).send({
      statusCode: 403,
      message: 'Forbidden',
    });
};
