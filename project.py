import pygame, sys
from pygame.locals import *
import math
import random

####################
# Helper Functions #
####################

# Takes two numbers.
# Returns a with the same sign as b.
# If b is 0, returns 0.
def sameSign(a, b):
	if b < 0:
		return -abs(a)
	elif b > 0:
		return abs(a)
	else:
		return 0


########################
# Random Map Generator #
########################

# Generates a 2d list which contains information about the map.
# Different contours make the map more varied.
def generateRandomMap(data):
	data.map = []
	for row in xrange(data.rows): data.map += [[0]*data.cols]
	middleRow = (data.lowestRow+data.highestRow)/2 # The starting point for the map.

	# Defining the tile types
	air = 0
	ground = 1

	generateLandscape(data, (middleRow, 0))	# Create the top landscape
	fillGround(data, data.cols)				# Fill in the underground


# Given a map and the tile to begin with, generates  
# a random landscape until the last col of the map.
def generateLandscape(data, cell):
	# Defining the chances
	if data.contour == "Mountains":
		chances = (.4, .8)
	elif data.contour == "Hills":
		chances = (.3, .6)
	else:
		chances = (.2, .4)

	row,col = cell
	while col <= len(data.map[0])-1:
		data.map[row][col] = 1 # Set the cell to be a surface.
		xPosition = col*data.tileSize - data.cameraAdjustDistance
		yPosition = row*data.tileSize
		Ground(xPosition, yPosition).add(data.terrain)

		randomValue = random.randint(0,10)*.1 # This float determines direction.

		if randomValue <= chances[0] and row < data.lowestRow:
			row += 1 # down
		elif randomValue <= chances[1] and row > data.highestRow:
			row -= 1 # up
		else:
			col += 1 # horizontal


def createNewCols(data, colsToAdd):
	lastCol = len(data.map[0]) - 1
	for row in xrange(len(data.map)):
		if data.map[row][lastCol] == 1:
			surfaceRow = row

	for row in xrange(len(data.map)):
		data.map[row] += [0]*colsToAdd

	if len(data.map[0])%20 == 0 and data.inMenu == False:
		spawnJumperEnemyOffScreen(data)

	generateLandscape(data, (surfaceRow,lastCol))

	fillGround(data, colsToAdd)


def fillGround(data, colsToFill):
	for col in xrange(len(data.map[0])-colsToFill, len(data.map[0])):
		xPosition = col*data.tileSize - data.cameraAdjustDistance
		placeUnderGroundTile = False
		for row in xrange(len(data.map)):
			yPosition = row*data.tileSize
			if data.map[row][col] == 1:
				placeUnderGroundTile = True
			elif data.map[row][col] == 0:
				if placeUnderGroundTile == True:
					data.map[row][col] = 2
					Underground(xPosition, yPosition).add(data.underground)


#####################
# Class Definitions #
#####################

class PhysicalObject(pygame.sprite.Sprite):
	# Physical Air Constants
	terminalVelocity = 10.0
	airDrag = 5.0
	gravity = 1.0

	# Physical Ground Constants
	groundFriction = .4

	# Physical Wall Constants
	wallGravity = .5
	wallTerminalVelocity = 5

	# Gravitates a physical object.
	def gravitate(self, data):
		# Normal gravity if the player is in the air.
		if (self.isGrounded == False and
			self.isWallSliding == False and
			self.dy < PhysicalObject.terminalVelocity):
			self.dy += PhysicalObject.gravity

		# Lessened gravity which is terrain dependent otherwise.
		elif (self.isWallSliding == True and
			self.dy < PhysicalObject.wallTerminalVelocity):
			self.dy += PhysicalObject.wallGravity

	def drag(self):
		if self.isGrounded == True:
			if self.dx > PhysicalObject.groundFriction:
				self.dx -= PhysicalObject.groundFriction
			elif self.dx < -PhysicalObject.groundFriction:
				self.dx += PhysicalObject.groundFriction
			else:
				self.dx = 0


# This class contains the information about the player.
class Player(PhysicalObject):
	playerFacingLeft = pygame.image.load("images/robotFacingLeft.png")
	playerFacingRight = pygame.image.load("images/robotFacingRight.png")
	playerStanding = pygame.image.load("images/robotStanding.png")

	def __init__(self, x, y):
		# Create Sprite
		pygame.sprite.Sprite.__init__(self)
		self.image = Player.playerFacingRight
		self.rect = self.image.get_rect()
		self.rect.x = x
		self.rect.y = y

		# Combat Constants
		self.hp = 10

		# Movement constants
		self.dx = 0
		self.dy = 0

		# Ground movement
		self.acceleration = .4
		self.groundDeceleration = 3.0
		self.dashMultiplier = 2.0
		self.topSpeed = 5.0

		# Jumping
		self.jumpPower = 14
		self.secondJumpAvailable = True
		self.wallJumpAngle = math.pi/3

		# State
		self.isGrounded = False
		self.isDashing = False
		self.isWallSliding = False
		self.wallSlide = None # Set to "Right" or "Left" depending on the wall's direction.
		self.isWallJumpAvailable = False
		self.isStunned = False
		self.alive = True

		# Controller state
		self.joystickDirection = None
		self.playerDirection = "Right"

		self.keyBoardLeft = False
		self.keyBoardRight = False

		# Cooldowns
		self.dashCooldown = 0
		self.dashDuration = 10
		self.isWallJumpAvailableCoolDown = 0
		self.isWallJumpAvailableDuration = 5
		self.stunCooldown = 0
		self.stunDuration = 20
		self.hasCollidedWithGroundDuration = 5
		self.hasCollidedWithGroundCooldown = 0

		# Collisions
		self.edgeAmount = 3 # The amount the character can stand off an edge.

	def setDirection(self):
		if self.playerDirection == "Right":
			self.image = Player.playerFacingRight
		else:
			self.image = Player.playerFacingLeft

	# Called in the player's update function.
	# Changes the player's movement and position.
	def applyPhysics(self, data):
		self.gravitate(data)
		self.playerCollisions(data)

	# Resolves the collisions for a player.
	def playerCollisions(self, data):
		# Checks for collision between the player and the sprites in the terrain group.
		collided = False
		for collision in pygame.sprite.spritecollide(self, data.terrain, False):
			collided = True
			ceilingDistance = abs(collision.rect.bottom - self.rect.top)
			groundDistance = abs(collision.rect.top - self.rect.bottom)
			rightWallDistance = abs(collision.rect.right - self.rect.left)
			leftWallDistance = abs(collision.rect.left - self.rect.right)

			# The minimum among these distances will partly determine the collision.
			lowToHigh = sorted([ceilingDistance] + [groundDistance] +
						  [rightWallDistance] + [leftWallDistance])

			# If the minimum values are close enough, it is a corner hit,
			# and we don't count it.
			cornerHit = False
			if abs(lowToHigh[0] - lowToHigh[1]) < 1:
				cornerHit = True

			if cornerHit == False:
				# Now we compare and decide.
				if rightWallDistance == lowToHigh[0]:
					self.rect.left = collision.rect.right
					self.hitWall("Right")
				elif leftWallDistance == lowToHigh[0]:
					self.rect.right = collision.rect.left
					self.hitWall("Left")
				elif (groundDistance == lowToHigh[0] or groundDistance < abs(self.dy)):
					self.rect.bottom = collision.rect.top + 1
					self.hitFloor()
				else:
					self.rect.top = collision.rect.bottom
					self.hitCeiling()
		if collided == False:
			self.isGrounded = False
			self.isWallSliding = False

		if self.rect.left < 0 or self.rect.right > data.width:
			self.hitBoundary(data)

	def adjustCamera(self, data):
		if data.cameraLock == False:
			if self.rect.right > data.cameraScrollPoint:
				adjustment = data.cameraScrollPoint - self.rect.right
				for sprite in data.terrain:
					sprite.rect.move_ip(adjustment, 0)
				for sprite in data.underground:
					sprite.rect.move_ip(adjustment, 0)
				for sprite in data.players:
					sprite.rect.move_ip(adjustment, 0)
				for sprite in data.bullets:
					sprite.rect.move_ip(adjustment, 0)
				for sprite in data.enemies:
					sprite.rect.move_ip(adjustment, 0)
				for sprite in data.finalBoss:
					sprite.rect.move_ip(adjustment, 0)
				for sprite in data.explosions:
					sprite.rect.move_ip(adjustment, 0)
				data.cameraAdjustDistance += abs(adjustment)
				data.score += abs(adjustment)

	def groundCollideCooldown(self):
		if self.hasCollidedWithGroundCooldown > 0:
			self.hasCollidedWithGroundCooldown -= 1

	# Updates the player model. Run every frame.
	def update(self, data):
		# Cooldowns
		self.dashCoolDown()
		self.wallJumpCoolDown()
		self.stunCooldownFn()
		self.groundCollideCooldown()

		# Movement
		if self.isDashing == True:
			# Horizontal speed is multiplied by the dash multiplier.
			self.rect.move_ip(self.dx*self.dashMultiplier, self.dy)
		else:
			self.rect.move_ip(self.dx, self.dy)

		if data.keyboardMode == True:
			if self.keyBoardRight == True:
				self.move("Right")
			if self.keyBoardLeft == True:
				self.move("Left")
			elif self.keyBoardLeft == False and self.keyBoardRight == False:
				self.control("No Direction", data)

		# Physics
		self.applyPhysics(data)
		self.adjustCamera(data)

		if self.hp <= 0:
			self.alive = False
			if len(data.players.sprites()) == 1:
				data.displayScore = True
			data.explosions.add(Explosion(self.rect.centerx, self.rect.centery))
			pygame.mixer.Sound.play(data.deathSound)
			self.remove(data.players)

	def stunCooldownFn(self):
		if self.isStunned == True and self.stunCooldown > 0:
			self.stunCooldown -= 1

		if self.stunCooldown == 0:
			self.isStunned = False

	# Sets isDashing to True and resets the dashCooldown.
	def dash(self):
		if self.isGrounded == True or self.isWallSliding == True:
			self.isDashing = True
			self.dashCooldown = self.dashDuration

	# Lowers the dash cooldown.
	def dashCoolDown(self):
		if self.isDashing == True and self.dashCooldown > 0:
			self.dashCooldown -= 1

		# If the player is grounded and the cooldown is 0, reset the dash.
		if self.dashCooldown == 0 and self.isGrounded == True:
			self.isDashing = False

	# Sets the player's y-movement to the terminal velocity.
	def fastFall(self):
		if self.isGrounded == False:
			self.dy = PhysicalObject.terminalVelocity

	# Performs a jump.
	# The player has a ground jump and a double jump.
	def jump(self, data):
		# If the player is on the ground, do a normal jump.
		if self.isGrounded == True:
			pygame.mixer.Sound.play(data.jumpSound2)
			self.dy = -self.jumpPower
			self.isGrounded = False
			self.secondJumpAvailable = True
		# If the player is sliding on a wall, jump some degrees above the horizontal.
		elif self.isWallJumpAvailable == True:
			pygame.mixer.Sound.play(data.jumpSound2)
			self.dy = -self.jumpPower*math.sin(self.wallJumpAngle)
			if self.wallSlide == "Right":
				self.dx = self.jumpPower*math.cos(self.wallJumpAngle)
			elif self.wallSlide == "Left":
				self.dx = -self.jumpPower*math.cos(self.wallJumpAngle)
			self.secondJumpAvailable = True
			self.isWallSliding = False
			self.isWallJumpAvailable = False
		# If the player is in the air, do another normal jump straight up.
		elif self.secondJumpAvailable == True:
			pygame.mixer.Sound.play(data.jumpSound)
			self.dy = -self.jumpPower
			self.secondJumpAvailable = False

	def wallJumpCoolDown(self):
		if self.isWallJumpAvailableCoolDown > 0:
			self.isWallJumpAvailableCoolDown -= 1
		else:
			self.isWallJumpAvailable = False

	def jumpReleased(self):
		if self.dy < 0:
			self.dy = 0	

	# Run when collided with the top of a tile.
	def hitFloor(self):
		if self.dy < 0:
			pass
		else:
			self.dy = 0
			self.isGrounded = True
			self.secondJumpAvailable = False
			self.isWallSliding = False
			self.hasCollidedWithGroundCooldown = self.hasCollidedWithGroundDuration

	# Run when collided with the bottom of a tile.
	def hitCeiling(self):
		# Reverse the dy and half its magnitude if going up.
		if self.dy < 0: self.dy = -self.dy/2

	def hitWall(self, direction):
		if self.hasCollidedWithGroundCooldown == 0:
			self.dx = 0
			self.playerDirection = direction
			self.setDirection()
		if self.joystickDirection != None:
			self.wallSlide = direction
			self.isWallSliding = True
			self.isWallJumpAvailable = True
			self.isWallJumpAvailableCoolDown = self.isWallJumpAvailableDuration
			self.isGrounded = False
		else:
			self.wallSlide = None
			self.isWallSliding = False

	def hitBoundary(self, data):
		self.dx = 0
		if self.rect.left <= 0:
			self.rect.left = 1
		elif self.rect.right >= data.width:
			self.rect.right = data.width - 1

	def move(self, direction):
		if direction == "Left":
			# The speed is in the normal "moving left" range.
			if self.dx <= 0 and self.dx > -self.topSpeed:
				self.dx -= self.acceleration
			# The speed is in the opposite direction moving quickly.
			elif self.dx >= self.groundDeceleration:
				self.dx -= self.groundDeceleration
			# The speed is in the opposite direction moving very slowly.
			elif self.dx >= 0 and self.dx < self.groundDeceleration:
				self.dx = 0
			# Do nothing if exceeding the top speed to the left.
		elif direction == "Right":
			# The speed is in the normal "moving left" range.
			if self.dx >= 0 and self.dx < self.topSpeed:
				self.dx += self.acceleration
			# The speed is in the opposite direction moving quickly.
			elif self.dx <= -self.groundDeceleration:
				self.dx += self.groundDeceleration
			# The speed is in the opposite direction moving very slowly.
			elif self.dx <= 0 and self.dx > -self.groundDeceleration:
				self.dx = 0
			# Do nothing if exceeding the top speed to the left.
		if self.isWallJumpAvailableCoolDown == 0:
			self.playerDirection = direction
			self.setDirection()

	def shoot(self, data):
		if self.alive == True:
			data.bullets.add(Bullet(self.rect.centerx, self.rect.centery-9,
								 	self.playerDirection, self.dx, data))

	# Player controls and effects on movement.
	def control(self, event, data):

		# Directional Commands

		# Changes the player's dx.
		if event == "Left" or event == "Right":
			self.move(event)
			self.joystickDirection = event

		# Resists sliding motion on the ground or in air.
		elif event == "No Direction":
			self.drag()
			self.joystickDirection = None

		# Changes the player's dy to terminal velocity if falling.
		elif event == "Down":
			self.fastFall()
			self.drag()

		# Action Commands

		# Changes the player's dy to the jump power if a jump is available.
		elif event == "Jump":
			self.jump(data)

		# Doubles the player's dx for a short time.
		elif event == "Dash":
			self.dash()

		elif event == "Shoot":
			self.shoot(data)

		# When the player releases his jump button, he no longer travels up.
		elif event == "Jump Released":
			self.jumpReleased()
		
		elif event == "Pause":
			if data.paused == True:
				data.paused = False
				pygame.mixer.unpause()
			else:
				pygame.mixer.pause()
				pygame.mixer.Sound.play(data.pauseSound)
				data.paused = True


class Bullet(pygame.sprite.Sprite):
	bulletImageRight = pygame.image.load("images/shotFacingRight.png")
	bulletImageLeft = pygame.image.load("images/shotFacingLeft.png")

	def __init__(self, x_location, y_location, direction, additionalSpeed, data):
		pygame.sprite.Sprite.__init__(self)

		# Constants
		bulletSpeed = 20

		# Properties
		if direction == "Right":
			self.direction = "Right"
			self.dx = bulletSpeed + additionalSpeed
			self.image = Bullet.bulletImageRight
		else:
			self.direction = "Left"
			self.dx = -bulletSpeed + additionalSpeed
			self.image = Bullet.bulletImageLeft

		self.dy = 0
		self.rect = self.image.get_rect()
		self.rect.x = x_location
		self.rect.y = y_location


	def update(self, data):
		# Movement
		self.rect.move_ip(self.dx, self.dy)

		# Check for collisions
		self.collisions(data)

		# Check if bullet is off screen
		if self.rect.x < 0 or self.rect.x > data.width:
			self.remove(data.bullets)


	def collisions(self, data):
		# A collision with the terrain will cause the bullets to disappear.
		pygame.sprite.groupcollide(data.bullets, data.terrain, True, False)


class Ground(pygame.sprite.Sprite):
	tileImage = pygame.image.load("images/green.png")

	def __init__(self, x_location, y_location):
		pygame.sprite.Sprite.__init__(self)

		self.image = Ground.tileImage
		self.rect = self.image.get_rect()

		self.rect.x = x_location
		self.rect.y = y_location

	def update(self, data):
		if self.rect.right < -data.rumblePower:
			self.remove(data.terrain)


class Underground(pygame.sprite.Sprite):
	tileImage = pygame.image.load("images/brown.png")

	def __init__(self, x_location, y_location):
		pygame.sprite.Sprite.__init__(self)

		self.image = Underground.tileImage
		self.rect = self.image.get_rect()

		self.rect.x = x_location
		self.rect.y = y_location

	def update(self, data):
		if self.rect.right < -data.rumblePower:
			self.remove(data.underground)


# The moon is the timer of the game, like a game event. When the timer becomes
# zero, the final boss appears.
class Moon(pygame.sprite.Sprite):
	phaseImage = [0,0,0,0,0,0,0,0]
	phaseImage[0] = pygame.image.load("images/phaseZero.png") # Full Moon
	phaseImage[1] = pygame.image.load("images/phaseOne.png") # Begin waning
	phaseImage[2] = pygame.image.load("images/phaseTwo.png")
	phaseImage[3] = pygame.image.load("images/phaseThree.png")
	phaseImage[4] = pygame.image.load("images/phaseFour.png")
	phaseImage[5] = pygame.image.load("images/phaseFive.png")
	phaseImage[6] = pygame.image.load("images/phaseSix.png")
	phaseImage[7] = pygame.image.load("images/phaseSeven.png") # Crescent moon

	def __init__(self, x_location, y_location):
		pygame.sprite.Sprite.__init__(self)

		self.image = pygame.image.load("images/phaseZero.png")

		self.rect = self.image.get_rect()

		self.rect.x = x_location
		self.rect.y = y_location

		self.currentPhase = 0

		# Cooldown between phases
		self.phaseDuration = 175
		self.phaseCooldown = self.phaseDuration

	def update(self, data):
		if data.inMenu == False:
			if self.phaseCooldown > 0:
				self.phaseCooldown -= 1
			elif self.currentPhase < 8:
				self.image = Moon.phaseImage[self.currentPhase]
				self.currentPhase += 1
				self.phaseCooldown = self.phaseDuration
			elif self.currentPhase == 8:
				finalBossEvent(data)
				pygame.mixer.Sound.play(data.earthquakeSound)


class jumperEnemy(PhysicalObject):
	enemyImage = pygame.image.load("images/red.png")

	def __init__(self, x_location, y_location):
		pygame.sprite.Sprite.__init__(self)

		self.image = jumperEnemy.enemyImage
		self.rect = self.image.get_rect()

		self.rect.x = x_location
		self.rect.y = y_location

		# Movement variables
		self.dx = 0
		self.dy = 0
		self.horizontalTopSpeed = 15
		self.verticalTopSpeed = 20
		self.isGrounded = False
		self.isWallSliding = False

		# Attack Variables
		self.damage = 1
		self.knockback = 10

	def update(self, data):
		# Movement
		self.rect.move_ip(self.dx, self.dy)

		# Physical Objects
		self.gravitate(data)

		# Intelligence
		averagePlayerDistance = 0
		players = 0
		distance = 0
		for player in data.players:
			players += 1
			distance += player.rect.centerx - self.rect.centerx
		if players != 0:
			distance = distance/players

		self.playerDirection = sameSign(1, (distance - self.rect.centerx))

		# Collisions
		self.collisions(data)

	def hitPlayer(self, player, data):
		if player.isStunned == False:
			pygame.mixer.Sound.play(data.hurtSound)
			player.isStunned = True
			player.stunCooldown = player.stunDuration
			player.hp -= self.damage
			player.dx = sameSign(self.knockback, self.dx)
			player.dy = -self.knockback

	def collisions(self, data):
		for collision in pygame.sprite.spritecollide(self, data.terrain, False):
			horizontalVelocity = self.playerDirection*random.randint(5, self.horizontalTopSpeed)
			verticalVelocity = -random.randint(10, self.verticalTopSpeed)
			self.dx = horizontalVelocity
			self.dy = verticalVelocity

		for collision in pygame.sprite.spritecollide(self, data.players, False):
			self.hitPlayer(collision, data)

		for collision in pygame.sprite.spritecollide(self, data.bullets, False):
			collision.remove(data.bullets)
			Explosion(self.rect.centerx, self.rect.centery).add(data.explosions)
			data.score += 1000
			self.remove(data.enemies)

		if self.rect.left <= 0:
			self.rect.left = 0
			self.dx = -self.dx
		elif self.rect.right >= data.width:
			self.rect.right = data.width
			self.dx = -self.dx


class moonEnemy(jumperEnemy):
	enemyImage = pygame.image.load("images/bigMoon.png")
	explosionImage = [0,0,0,0]
	explosionImage[0] = pygame.image.load("images/moonExp0.png")
	explosionImage[1] = pygame.image.load("images/moonExp1.png")
	explosionImage[2] = pygame.image.load("images/moonExp2.png")

	def __init__(self, x_location, y_location):
		pygame.sprite.Sprite.__init__(self)
		self.image = moonEnemy.enemyImage

		self.rect = self.image.get_rect()

		self.rect.x = x_location
		self.rect.y = y_location


		# Movement
		self.dy = 0
		self.dx = 0

		self.horizontalTopSpeed = 30
		self.verticalTopSpeed = 50
		self.isGrounded = False
		self.isWallSliding = False

		# Combat Variables
		self.hp = 25
		self.damage = 1
		self.knockback = 15

		# Aesthetic
		self.rumbleDuration = 20
		self.rumbleCooldown = 0

		# Cooldowns
		self.soundCooldown = 0
		self.firstFrame = True

		# Timer
		self.timer = 0

	def rumbleCooldownFn(self, data):
		if self.rumbleCooldown > 0:
			self.rumbleCooldown -= 1
			if self.rumbleCooldown % 5 == 0:
				rumbleGame(data)

	def soundCooldownFn(self, data):
		if self.soundCooldown > 0:
			self.soundCooldown -= 1

	def update(self, data):
		# Timer
		self.timer += 1

		# Movement
		self.rect.move_ip(self.dx/2, self.dy/2)

		# Physical Objects
		self.gravitate(data)

		# Intelligence
		averagePlayerDistance = 0
		players = 0
		distance = 0
		for player in data.players:
			players += 1
			distance += player.rect.centerx - self.rect.centerx
		if players != 0:
			distance = distance/players

		self.playerDirection = sameSign(1, (distance - self.rect.centerx))

		# Cooldowns
		self.rumbleCooldownFn(data)
		self.soundCooldownFn(data)
		if self.firstFrame == True:
			pygame.mixer.Sound.play(data.moonBattleMusic)
			self.firstFrame = False

		# Collisions
		self.collisions(data)

		# Health
		if self.hp < 13:
			x = self.rect.centerx
			y = self.rect.centery
			self.image = moonEnemy.explosionImage[0]
			self.rect = self.image.get_rect()
			self.rect.centerx = x
			self.rect.centery = y

		if self.hp < 8:
			x = self.rect.centerx
			y = self.rect.centery
			self.image = moonEnemy.explosionImage[1]
			self.rect = self.image.get_rect()
			self.rect.centerx = x
			self.rect.centery = y
			xSign = random.choice([-1,1])
			ySign = random.choice([-1,1])

			randomX = xSign*random.randint(0,data.tileSize*5)
			randomY = ySign*random.randint(0, data.tileSize*5)
			if self.timer % 30 == 0:
				data.explosions.add(Explosion(x+randomX,y+randomY))


		if self.hp <= 0:
			data.score *= 2
			data.displayScore = True
			data.explosions.add(moonExplosion(self.rect.centerx, self.rect.centery))
			pygame.mixer.Sound.play(data.finalExplosionSound)
			pygame.mixer.Sound.stop(data.moonBattleMusic)
			self.remove(data.finalBoss)

	def collisions(self, data):
		for collision in pygame.sprite.spritecollide(self, data.terrain, False):
			if self.soundCooldown == 0:
				pygame.mixer.Sound.play(data.moonCrashSound)
				self.soundCooldown = 5
			horizontalVelocity = self.playerDirection*random.randint(5, self.horizontalTopSpeed)
			verticalVelocity = -random.randint(10, self.verticalTopSpeed)
			self.dx = horizontalVelocity
			self.dy = verticalVelocity
			self.rumbleCooldown = self.rumbleDuration

		for collision in pygame.sprite.spritecollide(self, data.players, False):
			self.hitPlayer(collision, data)

		for collision in pygame.sprite.spritecollide(self, data.bullets, False):
			data.bullets.remove(collision)
			self.hp -= 1

		if self.rect.left <= 0:
			self.rect.left = 0
			self.dx = -self.dx
		elif self.rect.right >= data.width:
			self.rect.right = data.width
			self.dx = -self.dx


class Explosion(pygame.sprite.Sprite):
	explosionImage = [0,0,0,0] # 4 frames
	explosionImage[0] = pygame.image.load("images/expZero.png")
	explosionImage[1] = pygame.image.load("images/expOne.png")
	explosionImage[2] = pygame.image.load("images/expTwo.png")
	explosionImage[3] = pygame.image.load("images/expThree.png")

	def __init__(self, x, y, playSound=True):
		pygame.sprite.Sprite.__init__(self)
		self.image = Explosion.explosionImage[0]

		self.rect = self.image.get_rect()
		self.rect.centerx = x
		self.rect.centery = y

		# Animation timings
		self.frameDuration = 5
		self.frameCooldown = self.frameDuration
		self.currentAnimation = 0

		# Sound
		self.playSound = playSound

	def update(self, data):
		# Sound
		if self.playSound == True:
			pygame.mixer.Sound.play(data.explosionSound)
		self.playSound = False
		# Animation
		self.explosionAnimation(data)

	def explosionAnimation(self,data):
		if self.frameCooldown > 0:
			self.frameCooldown -= 1
		else:
			self.currentAnimation += 1
			self.image = Explosion.explosionImage[self.currentAnimation]
			self.frameCooldown = self.frameDuration
			if self.currentAnimation == len(Explosion.explosionImage)-1:
				data.explosions.remove(self)


class moonExplosion(pygame.sprite.Sprite):
	frames = [0,0,0]
	frames[0] = pygame.image.load("images/moonExp0.png")
	frames[1] = pygame.image.load("images/moonExp1.png")
	frames[2] = pygame.image.load("images/moonExp2.png")

	def __init__(self,x,y):
		pygame.sprite.Sprite.__init__(self)
		self.image = moonExplosion.frames[0]
		self.rect = self.image.get_rect()
		self.rect.centerx = x
		self.rect.centery = y

		# Cooldowns and duration
		self.frameDuration = 10
		self.frameCooldown = self.frameDuration
		self.currentAnimation = 0
		self.updateTime = 100

	def update(self, data):
		# Animation
		self.updateTime -= 1
		self.explosionAnimation(data)
		if self.updateTime == 0:
			pygame.mixer.Sound.play(data.victoryMusic)
			self.remove(data.explosions)

	def explosionAnimation(self, data):
		if self.frameCooldown > 0:
			self.frameCooldown -= 1
		else:
			for smallExplosionNumber in xrange(3):
				xSign = random.choice([-1, 1])
				ySign = random.choice([-1, 1])
				randomX = xSign*random.randint(0,abs(self.rect.left-self.rect.centerx))
				randomY = ySign*random.randint(0,abs(self.rect.left-self.rect.centerx))
				data.explosions.add(Explosion(self.rect.centerx + randomX,
											 self.rect.centery + randomY, False))


class Heart(pygame.sprite.Sprite):
	blueHeart = pygame.image.load("images/blueHeart.png")
	orangeHeart = pygame.image.load("images/orangeHeart.png")

	def __init__(self, xPosition, yPosition, playerNumber):
		pygame.sprite.Sprite.__init__(self)
		if playerNumber == 0:
			self.image = Heart.blueHeart
		else:
			self.image = Heart.orangeHeart

		self.rect = self.image.get_rect()
		self.rect.centerx = xPosition
		self.rect.centery = yPosition


################################################
# Game creation, updating, and control systems #
################################################

def updateGame(data):
	if data.paused == False:
		# Update sprites and remove sprites which are off the screen.
		data.terrain.update(data)
		data.underground.update(data)
		data.players.update(data)
		data.bullets.update(data)
		data.enemies.update(data)
		data.moon.update(data)
		data.finalBoss.update(data)
		data.explosions.update(data)
		updateHealth(data)

		# Create new terrain as the player moves
		if len(data.terrain.sprites()) < 400:
			createNewCols(data, 1)

		# Checks if the final boss sequence has begun and what stage it's in.
		if data.finalBossBegun == True and data.finalBossDelay > 0:
			data.finalBossDelay -= 1
			if data.finalBossDelay%5 == 0:
				rumbleGame(data)
		elif data.finalBossBegun == True and data.finalBossDelay == 0:
			data.finalBossBegun = False
			data.finalBoss.add(moonEnemy(data.width/2, -200))


def rumbleGame(data):
	if data.rumbleDirection == "Left":
		data.rumbleDirection = "Right"
		for sprite in data.terrain:
			sprite.rect.move_ip(-data.rumblePower,0)
		for sprite in data.underground:
			sprite.rect.move_ip(-data.rumblePower,0)
		for sprite in data.players:
			sprite.rect.move_ip(-data.rumblePower,0)
		data.cameraAdjustDistance += data.rumblePower
	elif data.rumbleDirection == "Right":
		data.rumbleDirection = "Left"
		for sprite in data.terrain:
			sprite.rect.move_ip(data.rumblePower,0)
		for sprite in data.underground:
			sprite.rect.move_ip(data.rumblePower,0)
		for sprite in data.players:
			sprite.rect.move_ip(data.rumblePower,0)
		data.cameraAdjustDistance -= data.rumblePower


def spawnJumperEnemyOffScreen(data):
	data.enemies.add(jumperEnemy((data.width+data.tileSize),data.tileSize))


def updateHealth(data):
	yPosition = data.tileSize
	xPosition = data.tileSize

	data.displayHealth = pygame.sprite.Group()
	playerHealth = [[],[]]

	playerNumber = 0
	for health in xrange(data.player.hp):
		heart = Heart(xPosition, yPosition, playerNumber)
		playerHealth[playerNumber].append(heart)
		data.displayHealth.add(playerHealth[playerNumber][health])
		xPosition += data.tileSize


def drawGame(data):
	data.moon.draw(data.surface)
	data.bullets.draw(data.surface)
	data.finalBoss.draw(data.surface)
	data.enemies.draw(data.surface)
	data.players.draw(data.surface)
	data.underground.draw(data.surface)
	data.terrain.draw(data.surface)
	data.explosions.draw(data.surface)
	data.displayHealth.draw(data.surface)
	if data.displayScore == True:
		if data.score > data.highScore:
			data.highScore = data.score
		score = data.gameFont.render(("Score: %d") % data.score, 1, (255,255,255))
		data.surface.blit(score, (2*data.width/5, data.height/3))
		score = data.gameFont.render(("HighScore: %d") % data.score, 1, (255,255,255))
		data.surface.blit(score, (2*data.width/5-data.tileSize*2, data.height/3+data.tileSize))
	if data.paused == True:
		pause = data.gameFont.render("PAUSED", 1, (255,255,255))
		data.surface.blit(pause, (2*data.width/5, data.tileSize))


def initMenu(data):
	# Menu
	data.inMenu = True
	data.splashCoolDown = 25
	data.white = (255,255,255)
	data.yellow = (255, 200, 0)
	data.startColor = (0,255,0)
	data.terrainChoiceColor = (255,255,255)
	data.helpMenu = 0

	# Create the surface
	data.height = 632
	data.width = 964
	data.surface = pygame.display.set_mode((data.width, data.height))
	surfaceColor = (0,0,0)
	data.surface.fill(surfaceColor)
	pygame.display.set_caption("New Moon")
	data.gameFont = pygame.font.Font("fonts/PressStart2P.ttf", 24)
	data.gameSmallFont = pygame.font.Font("fonts/PressStart2P.ttf", 14)

	# Set up the game clock
	data.fpsClock = pygame.time.Clock()

	# Allow pausing
	data.paused = False

	# Create the camera and rumble effect
	data.cameraScrollPoint = 2*data.width/3
	data.cameraAdjustDistance = 0
	data.cameraLock = False
	data.rumbleDirection = "Left"
	data.rumblePower = 20

	# Create the moving terrain
	data.rows = 20
	data.cols = 30
	data.tileSize = Ground.tileImage.get_rect().width
	underground = 2
	surface = 1
	air = 0
	data.highestRow = 10 # The highest row. Past this point the map can no longer go up.
	data.lowestRow = data.rows - 2 # Past this point the map can no longer go down.
	data.terrain = pygame.sprite.Group()
	data.underground = pygame.sprite.Group()
	data.colsGenerated = 0
	data.contour = "Plains"
	data.contours = ["Plains", "Hills", "Mountains"]
	data.contourIndex = 0
	generateRandomMap(data)

	# Create the list of enemies
	data.enemies = pygame.sprite.Group()

	# Create the empty list of bullets
	data.bullets = pygame.sprite.Group()

	# Create the empty list of explosions
	data.explosions = pygame.sprite.Group()

	# Create the empty list for the final boss
	data.finalBoss = pygame.sprite.Group()
	data.finalBossDelay = 100
	data.finalBossBegun = False

	# Create the moon
	data.moon = pygame.sprite.Group(Moon(data.width-200, 200))


def drawMenu(data):
	if data.splashCoolDown == 0:		
		data.moon.draw(data.surface)
		data.underground.draw(data.surface)
		data.terrain.draw(data.surface)
		start = data.gameFont.render("Start game", 1, (data.startColor))
		data.surface.blit(start, (data.width/8, data.height/4))
		terrainChoice = data.gameFont.render(data.contour, 1,
											 data.terrainChoiceColor)
		data.surface.blit(terrainChoice, (data.width/8, data.height/4+data.tileSize))
		if data.helpMenu == 0:
			help = data.gameSmallFont.render("for controls", 1, data.white)
			data.surface.blit(help, (data.width-data.tileSize*8, data.tileSize*2))
			h = data.gameSmallFont.render("'y'", 1, data.yellow)
			data.surface.blit(h, (data.width-data.tileSize*6, data.tileSize))
		elif data.helpMenu == 1:
			controls1 = data.gameSmallFont.render("Joystick to move", 1, data.white)
			controls2 = data.gameSmallFont.render("Middle X to restart", 1, data.white)
			controls3 = data.gameSmallFont.render("Blue x to shoot", 1, data.white)
			controls4 = data.gameSmallFont.render("Green A to jump", 1, data.white)
			controls5 = data.gameSmallFont.render("L or R to dash", 1, data.white)
			controls6 = data.gameSmallFont.render("Start to pause", 1, data.white)
			controls7 = data.gameSmallFont.render("L and R switch terrain", 1, data.white)
			data.surface.blit(controls1, (data.width-data.tileSize*10, data.tileSize))
			data.surface.blit(controls2, (data.width-data.tileSize*10, data.tileSize*1.5))
			data.surface.blit(controls3, (data.width-data.tileSize*10, data.tileSize*2))
			data.surface.blit(controls4, (data.width-data.tileSize*10, data.tileSize*2.5))
			data.surface.blit(controls5, (data.width-data.tileSize*10, data.tileSize*3))
			data.surface.blit(controls6, (data.width-data.tileSize*10, data.tileSize*3.5))
			data.surface.blit(controls7, (data.width-data.tileSize*10, data.tileSize*4))
	else:
		splash = data.gameFont.render(("-New Moon-"), 1, (255, 0, 0))
		data.surface.blit(splash, (2*data.width/5-data.tileSize, data.height/2))
		credit = data.gameFont.render(("15-112"), 1, (255, 0, 0))
		data.surface.blit(credit, (2*data.width/5+data.tileSize*.5,
								 data.height/2+data.tileSize))


def updateMenu(data):
	if data.splashCoolDown > 0:
		data.splashCoolDown -= 1
	else:
		data.terrain.update(data)
		data.underground.update(data)
		adjustment = -3
		for sprite in data.terrain:
			sprite.rect.move_ip(adjustment, 0)
		for sprite in data.underground:
			sprite.rect.move_ip(adjustment, 0)
		data.cameraAdjustDistance += abs(adjustment)

		# Create new terrain as the player moves
		if len(data.terrain.sprites()) < 400:
			createNewCols(data, 1)


def initSounds(data):
	data.deathSound = pygame.mixer.Sound("sounds/death.wav")
	data.deathSound.set_volume(.4)
	data.moonCrashSound = pygame.mixer.Sound("sounds/moonCrash.wav")
	data.explosionSound = pygame.mixer.Sound("sounds/explosion.wav")
	data.explosionSound.set_volume(.5)
	data.earthquakeSound = pygame.mixer.Sound("sounds/earthquake.wav")
	data.finalExplosionSound = pygame.mixer.Sound("sounds/finalExplosion.wav")
	data.jumpSound = pygame.mixer.Sound("sounds/jump.wav")
	data.jumpSound2 = pygame.mixer.Sound("sounds/jump2.wav")
	data.pauseSound = pygame.mixer.Sound("sounds/pause.wav")
	data.hurtSound = pygame.mixer.Sound("sounds/hurt.wav")
	data.moonBattleMusic = pygame.mixer.Sound("music/moonBattle.wav")
	data.moonBattleMusic.set_volume(.3)
	data.mountainMusic = pygame.mixer.Sound("music/armoredArmadillo.wav")
	data.mountainMusic.set_volume(.4)
	data.hillsMusic = pygame.mixer.Sound("music/launchOctopus.wav")
	data.hillsMusic.set_volume(.4)
	data.plainsMusic = pygame.mixer.Sound("music/stingChameleon.wav")
	data.plainsMusic.set_volume(.4)
	data.victoryMusic = pygame.mixer.Sound("music/victory.wav")
	data.victoryMusic.set_volume(.4)


def initGame(data):
	# Menu Conversion
	data.inMenu = False
	data.enemies.remove(data.enemies)
	data.cameraAdjustDistance = 0

	# Sound
	if data.contour == "Mountains":
		pygame.mixer.Sound.play(data.mountainMusic)
	elif data.contour == "Hills":
		pygame.mixer.Sound.play(data.hillsMusic)
	else:
		pygame.mixer.Sound.play(data.plainsMusic)

	# Create the player instance
	data.player = Player(50, 50)
	data.players = pygame.sprite.Group(data.player)

	# Create the terrain
	data.rows = 20
	data.cols = 30
	data.tileSize = Ground.tileImage.get_rect().width
	underground = 2
	surface = 1
	air = 0
	data.highestRow = 10 # The highest row. Past this point the map can no longer go up.
	data.lowestRow = data.rows - 2 # Past this point the map can no longer go down.
	data.terrain = pygame.sprite.Group()
	data.underground = pygame.sprite.Group()
	generateRandomMap(data)
	data.colsGenerated = 0

	# Create the moon
	data.moon = pygame.sprite.Group(Moon(data.width-200, 200))

	# Defining the display and score variables
	data.displayScore = False
	data.score = 0
	data.displayHealth = pygame.sprite.Group()


def finalBossEvent(data):
	pygame.sprite.Group.empty(data.moon)
	data.finalBossBegun = True
	data.cameraLock = True
	pygame.mixer.stop()


def joystickInit(data):
	try:
		data.joystick1 = pygame.joystick.Joystick(0)
		data.joystick1.init()
		data.keyboardMode = False
	except:
		data.keyboardMode = True

	# 0 Dpad Up
	# 1 Dpad Down
	# 2 Dpad Leftdad
	# 3 Dpad Right
	# 4 Start
	# 5 Select
	# 6 Left axis click
	# 7 Right axis click
	# 8 L
	# 9 R
	# 10 Middle
	# 11 A
	# 12 B
	# 13 X
	# 14 Y


#############
# Main Loop #
#############

def main():
	# Menu
	# Begin the game
	pygame.init()
	pygame.mixer.init()

	# Allowing data storage in a "data" variable
	class Struct():
		pass

	data = Struct()
	data.highScore = 0

	joystickInit(data)

	# Create and begin drawing the menu.
	initSounds(data)
	initMenu(data)
	startGame = False
	while True:
		if startGame == True:
			initMenu(data)
		startGame = False

		for event in pygame.event.get():
			if event.type == QUIT:
				pygame.quit()
				sys.exit()
			if data.keyboardMode == False:
				if event.type == JOYBUTTONDOWN:
					if event.button == 11:
						startGame = True
					elif event.button == 8:
						data.contourIndex -= 1
						if data.contourIndex == -4:
							data.contourIndex = 2
						data.contour = data.contours[data.contourIndex]
					elif event.button == 9:
						data.contourIndex += 1
						if data.contourIndex == 3:
							data.contourIndex = -3
						data.contour = data.contours[data.contourIndex]
					elif event.button == 14:
						data.helpMenu += 1
			else:
				if event.type == KEYDOWN:
					if event.key == K_RETURN:
						startGame = True
					elif event.key == K_y:
						data.helpMenu += 1
					elif event.key == K_d:
						data.contourIndex += 1
						if data.contourIndex == 3:
							data.contourIndex = -3
						data.contour = data.contours[data.contourIndex]							
					elif event.key == K_a:
						data.contourIndex -= 1
						if data.contourIndex == -4:
							data.contourIndex = 2
						data.contour = data.contours[data.contourIndex]

		data.surface.fill((0,0,0))
		updateMenu(data)
		drawMenu(data)
		pygame.display.update()
		data.fpsClock.tick(60)

		if startGame == True:
			startGame = False
			# Initiate the game
			initGame(data)

			# Main loop
			while True:

				# Button controls
				for event in pygame.event.get():
					# Quitting
					if event.type == QUIT:
						pygame.quit()
						sys.exit()

					elif data.keyboardMode == False:
						# Joystick controls
						if event.type == JOYBUTTONDOWN:

							# Movement Modifiers
							if event.button == 8 or event.button == 9:
								data.player.control("Dash", data)

							elif event.button == 11:
								data.player.control("Jump", data)

							elif event.button == 13:
								data.player.control("Shoot", data)

							elif event.button == 10:
								startGame = True

							elif event.button == 4:
								data.player.control("Pause", data)

						elif event.type == JOYBUTTONUP:

							# Movement Modifiers
							if event.button == 11:
								data.player.control("Jump Released", data)

					elif data.keyboardMode == True:
						if event.type == KEYDOWN:

							# Controls
							if event.key == K_a:
								data.player.keyBoardLeft = True

							elif event.key == K_d:
								data.player.keyBoardRight = True

							elif event.key == K_s:
								data.player.control("Down", data)

							elif event.key == K_SPACE:
								data.player.control("Jump", data)

							elif event.key == K_w:
								data.player.control("Jump", data)

							elif event.key == K_m:
								data.player.control("Shoot", data)

							elif event.key == K_n:
								data.player.control("Dash", data)

							elif event.key == K_p:
								data.player.control("Pause", data)

							elif event.key == K_r:
								startGame = True

						elif event.type == KEYUP:

							if event.key == K_SPACE:
								data.player.control("Jump Released", data)

							if event.key == K_w:
								data.player.control("Jump Released", data)

							elif event.key == K_d:
								data.player.keyBoardRight = False

							elif event.key == K_a:
								data.player.keyBoardLeft = False



				# Joystick Axis Controls

				if data.keyboardMode == False:
					x_axis = data.joystick1.get_axis(0)
					y_axis = data.joystick1.get_axis(1)
					if y_axis > .7: data.player.control("Down", data)
					elif x_axis < -.3: data.player.control("Left", data)
					elif x_axis > .3: data.player.control("Right", data)
					else: data.player.control("No Direction", data)


				# Draw and update the game
				data.surface.fill((0,0,0))
				updateGame(data)
				drawGame(data)
				pygame.display.update()

				if startGame == True:
					pygame.mixer.stop()
					break

				data.fpsClock.tick(60)

main()