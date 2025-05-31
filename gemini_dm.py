def notify_dm(message: str) -> None:
    """
    Sends a notification to the Dungeon Master.
    For now, it just prints the message to the console.
    """
    print(f"DM NOTIFICATION: {message}")

if __name__ == '__main__':
    # Example usage:
    notify_dm("Player Valerius has entered the Whispering Woods.")
    notify_dm("A goblin ambush is imminent!")
