'use-strict';

import * as UsersController from './users.controller.js';

import * as PaginationMiddleware from '../../middlewares/pagination.middleware.js';
import * as PermissionMiddleware from '../../middlewares/auth.permission.middleware.js';
import * as ValidationMiddleware from '../../middlewares/auth.validation.middleware.js';
import * as UserValidationMiddleware from '../../middlewares/user.validation.middleware.js';

/**
 * @swagger
 * tags:
 *  name: Users
 */

export const routesConfig = (app) => {
  /**
   * @swagger
   * /api/users:
   *   get:
   *     tags: [Users]
   *     security:
   *       - bearerAuth: []
   *     summary: Get all users
   *     parameters:
   *       - in: query
   *         name: start
   *         schema:
   *           type: number
   *         description: Start index
   *       - in: query
   *         name: page
   *         schema:
   *           type: number
   *         description: Page
   *       - in: query
   *         name: pageSize
   *         schema:
   *           type: number
   *         description: Page size
   *     responses:
   *       200:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/users', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('users:access'),
    UsersController.list,
    PaginationMiddleware.pages,
  ]);

  /**
   * @swagger
   * /api/users:
   *   post:
   *     tags: [Users]
   *     security:
   *       - bearerAuth: []
   *     summary: Creates new user
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *          schema:
   *            type: object
   *            properties:
   *              userId:
   *                type: string
   *              userName:
   *                type: string
   *              userDept:
   *                type: string
   *              password:
   *                type: string
   *              permissionLevel:
   *                type: integer
   *     responses:
   *       201:
   *         description: Successfull
   *       400:
   *         description: Bad request
   *       401:
   *         description: Unauthorized
   *       409:
   *         description: User already exists
   *       500:
   *         description: Internal server error
   */
  app.post('/api/users', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('admin'),
    UserValidationMiddleware.hasValidFields,
    UsersController.insert,
  ]);

  /**
   * @swagger
   * /api/users/{userId}:
   *   get:
   *     tags: [Users]
   *     security:
   *       - bearerAuth: []
   *     summary: Get specific user by userId or numeric ID
   *     parameters:
   *       - in: path
   *         name: userId
   *         schema:
   *           oneOf:
   *             - type: string
   *             - type: integer
   *         required: true
   *         description: User ID (can be numeric ID or userId string)
   *     responses:
   *       200:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.get('/api/users/:userId', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('users:access'),
    UsersController.getById,
  ]);

  /**
   * @swagger
   * /api/users/{userId}:
   *   patch:
   *     tags: [Users]
   *     security:
   *       - bearerAuth: []
   *     summary: Update specific user by userId
   *     parameters:
   *       - in: path
   *         name: userId
   *         schema:
   *           type: string
   *         required: true
   *         description: ID of the user
   *     responses:
   *       204:
   *         description: Successfull
   *       400:
   *         description: Bad request
   *       401:
   *         description: Unauthorized
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.patch('/api/users/:userId', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('admin'),
    UsersController.patchByName,
  ]);

  /**
   * @swagger
   * /api/users/{userId}:
   *   delete:
   *     tags: [Users]
   *     security:
   *       - bearerAuth: []
   *     summary: Delete user by userId
   *     parameters:
   *       - in: path
   *         name: userId
   *         schema:
   *           type: string
   *         required: true
   *         description: ID of the user
   *     responses:
   *       200:
   *         description: Successfull
   *       400:
   *         description: Bad request
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.delete('/api/users/:userId', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('admin'),
    UsersController.removeByName,
  ]);

  /**
   * @swagger
   * /api/users/access-history:
   *   get:
   *     tags: [Users]
   *     security:
   *       - bearerAuth: []
   *     summary: Get all users access history
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/users/access-history', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('users:access'),
    UsersController.getAccessHistory,
  ]);

  const routes = app._router.stack
    .filter(r => r.route)
    .map(r => ({
      path: r.route.path,
      method: Object.keys(r.route.methods)[0].toUpperCase()
    }));
  console.log('Registered user routes:', routes);
};
